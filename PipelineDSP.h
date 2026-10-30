// PIPELINE (Studio Wiga) - moteur audio
// Vibrato de hauteur a ligne de retard courte, d'apres le fonctionnement de l'EarthQuaker Devices Aqueduct :
//   Sine, Triangle, Ramp, Square : forme d'onde de la VARIATION DE HAUTEUR (le temps de retard est son integrale),
//   Random : « disque voile » a faible Depth, glissandos aleatoires de plus en plus desordonnes en montant Depth,
//   Env D  : LFO sinus a la vitesse Rate, l'attaque fixe l'intensite (Depth = sensibilite de l'enveloppe),
//   Env R  : l'attaque fixe la vitesse du LFO sinus (Rate = sensibilite, Depth = intensite),
//   Env P  : l'attaque fait plonger la hauteur comme un vibrato de guitare (Rate = sensibilite et amplitude,
//            Depth = melange sec / traite, seul mode avec signal sec : midi = 50/50 avec un peu d'annulation de phase).
// Tout le reste est 100 % traite (vrai vibrato). Aucune allocation dans process().
#pragma once
#include <vector>
#include <cmath>
#include <cstdint>
#include <atomic>
#include <algorithm>

namespace pipeline
{
    constexpr float kPi = 3.14159265358979f;

    enum Mode { Sine = 0, Triangle, Ramp, Square, Random, EnvD, EnvR, EnvP, numModes };

    struct Params
    {
        float rate  = 0.5f;      // 0..1 (potard RATE)
        float depth = 0.5f;      // 0..1 (potard DEPTH)
        int   mode  = Sine;
        bool  active = true;     // footswitch
        double syncHz = 0.0;     // > 0 : vitesse imposee par le tempo du DAW
        double syncPhase = -1.0; // >= 0 : phase attendue en debut de bloc (transport en lecture)
    };

    // vitesse du LFO (Hz) pour un potard 0..1 : 0,1 Hz a 16 Hz, midi ~ 1,9 Hz, 3 h ~ 4,5 Hz
    inline float rateToHz (float r)
    {
        r = std::clamp (r, 0.0f, 1.0f);
        return 0.1f * std::pow (160.0f, std::pow (r, 0.8f));
    }

    //==========================================================================
    // Tables de forme : D(phase) dans [0, 1] = temps de retard normalise (integrale de la hauteur, signe inverse)
    //==========================================================================
    struct ShapeTable
    {
        static constexpr int N = 4096;
        float d[N + 1] {};
        float maxSlope = 1.0f;      // max |dD / dphase|

        template <typename PitchFn>
        void build (PitchFn pitch)
        {
            std::vector<double> p (N);
            double mean = 0.0;
            for (int i = 0; i < N; ++i) { p[(size_t) i] = pitch ((double) i / N); mean += p[(size_t) i]; }
            mean /= N;
            std::vector<double> acc (N);
            double s = 0.0;
            for (int i = 0; i < N; ++i) { s -= (p[(size_t) i] - mean); acc[(size_t) i] = s; }   // hauteur vers le haut = retard qui diminue
            const double lo = *std::min_element (acc.begin(), acc.end()), hi = *std::max_element (acc.begin(), acc.end());
            const double span = std::max (1.0e-9, hi - lo);
            for (int i = 0; i < N; ++i) d[i] = (float) ((acc[(size_t) i] - lo) / span);
            d[N] = d[0];
            double ms = 0.0;
            for (int i = 0; i < N; ++i) ms = std::max (ms, std::abs ((double) d[i + 1] - d[i]) * N);
            maxSlope = (float) ms;
        }

        float at (double phase) const
        {
            const double x = phase * N;
            int i = (int) x;
            const float f = (float) (x - i);
            i = ((i % N) + N) % N;
            return d[i] + f * (d[i + 1] - d[i]);
        }
    };

    struct Tables
    {
        ShapeTable t[4];
        Tables()
        {
            // SINE : hauteur sinusoidale (vibrato d'ampli classique)
            t[Sine].build ([] (double ph) { return std::cos (2.0 * kPi * ph); });
            // TRIANGLE : montee et descente plus franches, coude marque au sommet de chaque cycle
            t[Triangle].build ([] (double ph) { return 1.0 - 4.0 * std::abs (ph - 0.5); });
            // RAMP : impulsion « sonar » vers le haut, pente descendante rapide, palier (sustain) puis retour (release)
            t[Ramp].build ([] (double ph)
            {
                const double a = 0.025;                       // attaque tres courte
                if (ph < a) return std::sin (0.5 * kPi * ph / a);
                const double sustain = -0.38;
                if (ph < 0.80) return sustain + (1.0 - sustain) * std::exp (-(ph - a) / 0.075);
                const double r = (ph - 0.80) / 0.20;          // release vers le centre
                const double atEnd = sustain + (1.0 - sustain) * std::exp (-(0.80 - a) / 0.075);
                return atEnd * (1.0 - r * r * (3.0 - 2.0 * r));
            });
            // SQUARE : deux hauteurs, passage quasi instantane (trille) ; flancs adoucis sur 4 % du cycle (pas de clic)
            t[Square].build ([] (double ph)
            {
                const double k = 14.0;                        // flancs raides mais continus
                return std::tanh (k * std::sin (2.0 * kPi * ph)) / std::tanh (k);
            });
        }
    };

    inline const Tables& tables() { static const Tables t; return t; }

    //==========================================================================
    struct OnePole
    {
        float a = 0.0f, z = 0.0f;
        void setTime (float seconds, float fs) { a = seconds <= 0.0f ? 0.0f : std::exp (-1.0f / (seconds * fs)); }
        float tick (float x) { z = x + a * (z - x); return z; }
    };

    // passe-bas 2 poles (Butterworth, forme TPT) : couleur « analogique » de la voie traitee
    struct LowPass2
    {
        float g = 0.0f, k = 1.41421356f, s1 = 0.0f, s2 = 0.0f;
        void set (float hz, float fs) { g = std::tan (kPi * std::min (hz, 0.45f * fs) / fs); }
        void reset() { s1 = s2 = 0.0f; }
        float tick (float x)
        {
            const float hp = (x - (k + g) * s1 - s2) / (1.0f + g * (k + g));
            const float bp = g * hp + s1; s1 = g * hp + bp;
            const float lp = g * bp + s2; s2 = g * bp + lp;
            return lp;
        }
    };

    //==========================================================================
    class Engine
    {
    public:
        // pour la fenetre (lus par le thread de l'interface)
        std::atomic<float> shownCents { 0.0f };    // ecart de hauteur instantane (cents)
        std::atomic<float> shownEnv   { 0.0f };    // enveloppe 0..1 (modes Env)
        std::atomic<float> shownLfo   { 0.5f };    // forme de modulation 0..1

        void prepare (double sampleRate, int numChannels)
        {
            fs = (float) sampleRate;
            nCh = std::clamp (numChannels, 1, 2);
            int size = 1;
            while (size < (int) (fs * 0.12f) + 8) size <<= 1;      // 120 ms : retard maxi + marge
            mask = size - 1;
            for (auto& b : buf) b.assign ((size_t) size, 0.0f);
            w = 0;
            for (int c = 0; c < 2; ++c) { lp[c].reset(); lp[c].set (7200.0f, fs); dcX[c] = dcY[c] = 0.0f; }
            dcR = std::exp (-2.0f * kPi * 12.0f / fs);
            envHp.setTime (1.0f / (2.0f * kPi * 90.0f), fs);
            envAtt = std::exp (-1.0f / (0.0015f * fs));
            envRel = std::exp (-1.0f / (0.140f * fs));
            smoothK = std::exp (-1.0f / (0.018f * fs));
            env = envSm = 0.0f;
            phase = 0.0; rndPhase = 0.0;
            rndA = rndB = 0.5f; rndLp1 = rndLp2 = 0.5f;
            bendDelay = 0.0f;
            curDelay = minDelaySamples();
            rateSm = -1.0f; depthSm = -1.0f;
            bypassMix = 1.0f;
            primed = false; xfade = 0.0f; oldDelay = curDelay;
            xfadeStep = 1.0f / (0.015f * fs);
            centreSm = 0.0f; centreK = std::exp (-1.0f / (0.4f * fs));
            dryG = 0.0f; wetG = 1.0f;
            rng = 0x2545F491u;
        }

        void process (float* const* io, int numChannels, int n, const Params& p)
        {
            const auto& tab = tables();
            const int ch = std::min (numChannels, nCh == 1 ? 1 : 2);
            const int mode = std::clamp (p.mode, 0, (int) numModes - 1);

            // phase calee sur le tempo du DAW (transport en lecture)
            if (p.syncHz > 0.0 && p.syncPhase >= 0.0 && (mode <= EnvD)) phase = p.syncPhase;

            const float targetBypass = p.active ? 1.0f : 0.0f;
            const float bypassStep = 1.0f / (0.012f * fs);           // fondu de « relais » 12 ms
            const float dMin = minDelaySamples();
            const float maxDelay = (float) mask - 4.0f;
            float sumCents = 0.0f, envShow = 0.0f, lfoShow = 0.0f;

            for (int i = 0; i < n; ++i)
            {
                // ---- reglages lisses (pas de « zipper ») ----
                // lissage a 2 poles (pedale d'expression sans saccades, potards sans « zipper »)
                if (rateSm < 0.0f) { rateSm = rateSm1 = p.rate; depthSm = depthSm1 = p.depth; }
                rateSm1  = p.rate  + smoothK * (rateSm1  - p.rate);
                depthSm1 = p.depth + smoothK * (depthSm1 - p.depth);
                rateSm   = rateSm1  + smoothK * (rateSm  - rateSm1);
                depthSm  = depthSm1 + smoothK * (depthSm - depthSm1);

                // ---- entree (mono pour le suiveur d'enveloppe) ----
                float mono = 0.0f;
                for (int c = 0; c < ch; ++c)
                {
                    const float x = io[c][i];
                    const float y = x - dcX[c] + dcR * dcY[c];      // bloque le continu
                    dcX[c] = x; dcY[c] = y;
                    buf[c][(size_t) w] = y;
                    mono += y;
                }
                mono /= (float) ch;

                // suiveur d'enveloppe (attaque du mediator) : passe-haut 90 Hz, crete, attaque 1,5 ms / relache 140 ms
                const float hpX = mono - envHp.tick (mono);
                const float rect = std::abs (hpX);
                env = rect > env ? rect + envAtt * (env - rect) : rect + envRel * (env - rect);

                // ---- temps de retard voulu (en echantillons) ----
                float hz = p.syncHz > 0.0 ? (float) p.syncHz : rateToHz (rateSm);
                float target = dMin;
                float lfoVal = 0.5f;

                switch (mode)
                {
                    case Sine: case Triangle: case Ramp: case Square:
                    {
                        const auto& t = tab.t[mode];
                        const float a = amplitudeSamples (depthSm, hz, t.maxSlope);
                        lfoVal = t.at (phase);
                        target = centreFor (dMin, a) + a * (lfoVal - 0.5f);
                        advance (hz);
                        break;
                    }
                    case Random:
                    {
                        // « disque voile » (rotation decentree, sinus) qui se defait en glissandos aleatoires avec Depth
                        const float chaos = std::clamp ((depthSm - 0.12f) / 0.70f, 0.0f, 1.0f);
                        stepRandom (hz, chaos);
                        const float wow = tab.t[Sine].at (phase);
                        lfoVal = (1.0f - chaos) * wow + chaos * rndLp2;
                        const float a = amplitudeSamples (depthSm, hz, kPi * (1.0f + 1.6f * chaos));
                        target = centreFor (dMin, a) + a * (lfoVal - 0.5f);
                        advance (hz);
                        break;
                    }
                    case EnvD:
                    {
                        // Depth = sensibilite : plus on attaque, plus le vibrato est profond
                        const float e = envAmount (depthSm);
                        envSm = e > envSm ? e + envSmAtt() * (envSm - e) : e + envSmRel() * (envSm - e);
                        const auto& t = tab.t[Sine];
                        const float aMax = amplitudeSamples (0.78f, hz, t.maxSlope);
                        lfoVal = t.at (phase);
                        // le centre reste celui de l'amplitude maxi : l'attaque n'ouvre que l'oscillation (pas de plongeon)
                        target = centreFor (dMin, aMax) + aMax * envSm * (lfoVal - 0.5f);
                        advance (hz);
                        envShow += envSm;
                        break;
                    }
                    case EnvR:
                    {
                        // Rate = sensibilite : l'attaque accelere le LFO (0,35 Hz au repos -> 13 Hz a fond)
                        const float e = envAmount (rateSm);
                        envSm = e > envSm ? e + envSmAtt() * (envSm - e) : e + envSmRel() * (envSm - e);
                        hz = 0.35f * std::pow (13.0f / 0.35f, envSm);
                        const auto& t = tab.t[Sine];
                        // au-dela de 3 Hz l'amplitude du retard diminue : le vibrato accelere sans devenir plus profond
                        const float a = amplitudeSamples (depthSm, hz, t.maxSlope) * std::min (1.0f, std::sqrt (3.0f / hz));
                        lfoVal = t.at (phase);
                        target = centreFor (dMin, amplitudeSamples (depthSm, 0.35f, t.maxSlope)) + a * (lfoVal - 0.5f);
                        advance (hz);
                        envShow += envSm;
                        break;
                    }
                    case EnvP:
                    {
                        // « My Bloody Valentine » : l'attaque allonge le retard en ~40 ms (la note plonge, comme un vibrato
                        // de guitare relache), puis le retard revient lentement (la note remonte a peine au-dessus).
                        // Rate = sensibilite et amplitude du bend.
                        const float e = envAmount (0.35f + 0.65f * rateSm);
                        const float range = (0.8f + 15.0f * rateSm * rateSm) * 0.001f * fs;   // jusqu'a ~16 ms
                        const float want = range * e;
                        const float att = std::exp (-1.0f / ((0.030f + 0.030f * rateSm) * fs));
                        const float rel = std::exp (-1.0f / ((0.35f + 0.45f * rateSm) * fs));
                        bendDelay = want > bendDelay ? want + att * (bendDelay - want) : want + rel * (bendDelay - want);
                        target = dMin + bendDelay;
                        centreSm = dMin;
                        lfoVal = range > 0.0f ? bendDelay / range : 0.0f;
                        envShow += e;
                        break;
                    }
                    default: break;
                }

                // discontinuite (demarrage, changement de mode, preset, saut du transport) : au lieu de faire glisser
                // le retard (plongeon de hauteur parasite), on bascule de tete de lecture avec un fondu de 15 ms
                target = std::clamp (target, 1.0f, maxDelay);
                if (! primed) { curDelay = target; primed = true; }
                else if (std::abs (target - curDelay) > jumpSamples() && xfade <= 0.0f)
                {
                    oldDelay = curDelay;
                    curDelay = target;
                    xfade = 1.0f;
                }
                // limiteur de pente : la hauteur reste entre -12 et +5 demi-tons (jamais de lecture a l'envers)
                const float maxUp = 0.50f, maxDown = 0.33f;   // marge au-dessus du plafond 0,28 des formes d'onde
                const float d = std::clamp (target - curDelay, -maxDown, maxUp);
                curDelay = std::clamp (curDelay + d, 1.0f, maxDelay);
                sumCents += 1200.0f * std::log2 (std::max (0.05f, 1.0f - d));
                lfoShow += lfoVal;
                const float xf = xfade;                        // part de l'ancienne tete de lecture
                if (xfade > 0.0f) xfade = std::max (0.0f, xfade - xfadeStep);

                // ---- lecture interpolee (Hermite 4 points) + couleur de la voie traitee ----
                // melange sec / traite : seulement en Env P (Depth) ; ailleurs 100 % traite (gains lisses au changement de mode)
                float dryT = 0.0f, wetT = 1.0f;
                if (mode == EnvP)
                {
                    dryT = std::min (1.0f, 2.0f * (1.0f - depthSm));
                    wetT = std::min (1.0f, 2.0f * depthSm);
                    const float norm = std::min (1.0f, 2.0f / (dryT + wetT + 1.0f));   // midi : 2 x 0,67 (pas de bond de volume)
                    dryT *= norm;
                    wetT *= norm;
                }
                dryG = dryT + smoothK * (dryG - dryT);
                wetG = wetT + smoothK * (wetG - wetT);
                if (bypassMix != targetBypass)
                    bypassMix = targetBypass > bypassMix ? std::min (targetBypass, bypassMix + bypassStep)
                                                         : std::max (targetBypass, bypassMix - bypassStep);
                for (int c = 0; c < ch; ++c)
                {
                    float wet = readAt (buf[c], curDelay);
                    if (xf > 0.0f)
                    {
                        const float g = xf * xf * (3.0f - 2.0f * xf);           // fondu en S
                        wet += g * (readAt (buf[c], oldDelay) - wet);
                    }
                    wet = lp[c].tick (wet);
                    wet = softSat (wet);
                    const float dry = io[c][i];
                    const float fx = dry * dryG + wet * wetG;
                    io[c][i] = dry + bypassMix * (fx - dry);
                }
                w = (w + 1) & mask;
            }

            shownCents.store (sumCents / (float) std::max (1, n), std::memory_order_relaxed);
            shownEnv.store (envShow / (float) std::max (1, n), std::memory_order_relaxed);
            shownLfo.store (lfoShow / (float) std::max (1, n), std::memory_order_relaxed);
        }

        float getLatencyHint() const { return minDelaySamples(); }

    private:
        // lecture interpolee (Hermite 4 points) a « delay » echantillons derriere la tete d'ecriture
        float readAt (const std::vector<float>& b, float delay) const
        {
            const float rp = (float) w - delay;
            const int i1 = (int) std::floor (rp);
            const float f = rp - (float) i1;
            const float xm1 = b[(size_t) ((i1 - 1) & mask)], x0 = b[(size_t) (i1 & mask)],
                        x1 = b[(size_t) ((i1 + 1) & mask)], x2 = b[(size_t) ((i1 + 2) & mask)];
            const float c1 = 0.5f * (x1 - xm1);
            const float c2 = xm1 - 2.5f * x0 + 2.0f * x1 - 0.5f * x2;
            const float c3 = 0.5f * (x2 - xm1) + 1.5f * (x0 - x1);
            return ((c3 * f + c2) * f + c1) * f + x0;
        }
        // centre du retard (echantillons) : suit l'amplitude voulue lentement (0,4 s) pour que tourner Depth
        // ou une attaque ne fasse pas glisser toute la hauteur ; un saut (preset) passe par le fondu de tetes
        float centreFor (float dMin, float a)
        {
            const float want = dMin + 0.5f * a;
            if (centreSm <= 0.0f || std::abs (want - centreSm) > 0.004f * fs) centreSm = want;
            else centreSm = want + centreK * (centreSm - want);
            return centreSm;
        }
        float jumpSamples() const { return 0.0015f * fs; }              // saut > 1,5 ms en un echantillon = discontinuite

        float minDelaySamples() const { return 0.0006f * fs + 2.0f; }    // 0,6 ms : petit decalage de phase (midi en Env P)

        // amplitude du retard (echantillons) pour un potard DEPTH 0..1 :
        // courbe progressive jusqu'a 22 ms, limitee pour que l'ecart de hauteur reste musical meme a vitesse maxi
        float amplitudeSamples (float depth, float hz, float maxSlope) const
        {
            const float dz = std::clamp ((depth - 0.01f) / 0.99f, 0.0f, 1.0f);
            const float aSec = 0.022f * std::pow (dz, 2.1f);
            const float capSec = 0.28f / (std::max (0.05f, hz) * std::max (0.5f, maxSlope));   // pente maxi 0,28 (~ +4,3 / -5,7 demi-tons)
            return std::min (aSec, capSec) * fs;
        }

        // niveau d'enveloppe 0..1 pour une sensibilite 0..1 (potard) ; micros faibles a moyens comme la pedale
        float envAmount (float sens) const
        {
            const float gainDb = -6.0f + 48.0f * std::clamp (sens, 0.0f, 1.0f);
            const float x = env * std::pow (10.0f, gainDb / 20.0f);
            return 1.0f - std::exp (-1.6f * x);
        }
        float envSmAtt() const { return std::exp (-1.0f / (0.012f * fs)); }
        float envSmRel() const { return std::exp (-1.0f / (0.280f * fs)); }

        void advance (float hz)
        {
            phase += (double) hz / (double) fs;
            if (phase >= 1.0) phase -= std::floor (phase);
        }

        float uniform()
        {
            rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5;
            return (float) (rng & 0xFFFFFF) / 16777215.0f;
        }

        // aleatoire : nouvelle cible a chaque demi-cycle (intervalles de plus en plus irreguliers), lisse sur 2 poles
        void stepRandom (float hz, float chaos)
        {
            rndPhase += (double) (hz * 2.0f) / (double) fs * (double) rndSpeed;
            if (rndPhase >= 1.0)
            {
                rndPhase -= std::floor (rndPhase);
                rndA = rndB;
                const float spread = 0.35f + 0.65f * chaos;
                rndB = std::clamp (0.5f + spread * (uniform() - 0.5f) * 2.0f * 0.5f + 0.0f, 0.0f, 1.0f);
                rndSpeed = 1.0f + chaos * 1.6f * (uniform() - 0.35f);           // tempo « ivre »
                rndSpeed = std::clamp (rndSpeed, 0.35f, 2.4f);
            }
            const float u = (float) rndPhase;
            const float target = rndA + (rndB - rndA) * u * u * (3.0f - 2.0f * u);
            const float k = std::exp (-2.0f * kPi * std::max (0.2f, hz * 2.5f) / fs);
            rndLp1 = target + k * (rndLp1 - target);
            rndLp2 = rndLp1 + k * (rndLp2 - rndLp1);
        }

        static float softSat (float x)
        {
            // saturation tres douce (au-dela de -6 dBFS seulement), transparente au niveau guitare normal
            const float t = 0.5f;
            const float ax = std::abs (x);
            if (ax <= t) return x;
            const float y = t + (1.0f - t) * std::tanh ((ax - t) / (1.0f - t));
            return x < 0.0f ? -y : y;
        }

        float fs = 48000.0f;
        int nCh = 2;
        std::vector<float> buf[2];
        int mask = 0, w = 0;
        LowPass2 lp[2];
        float dcX[2] {}, dcY[2] {}, dcR = 0.999f;
        OnePole envHp;
        float env = 0.0f, envSm = 0.0f, envAtt = 0.0f, envRel = 0.0f;
        float smoothK = 0.0f, rateSm = -1.0f, depthSm = -1.0f, rateSm1 = 0.0f, depthSm1 = 0.0f;
        double phase = 0.0, rndPhase = 0.0;
        float rndA = 0.5f, rndB = 0.5f, rndLp1 = 0.5f, rndLp2 = 0.5f, rndSpeed = 1.0f;
        float bendDelay = 0.0f, curDelay = 0.0f, oldDelay = 0.0f, xfade = 0.0f, xfadeStep = 0.001f;
        bool primed = false;
        float centreSm = 0.0f, centreK = 0.0f;
        float dryG = 0.0f, wetG = 1.0f;
        float bypassMix = 1.0f;
        uint32_t rng = 0x2545F491u;
    };
}
