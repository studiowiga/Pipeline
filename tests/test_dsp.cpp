// Banc d'essai du moteur Pipeline (hors plugin) : mesure de la hauteur instantanee et fichiers WAV par mode.
// g++ -O2 -std=c++17 tests/test_dsp.cpp -o test_dsp && ./test_dsp out/
#include "../PipelineDSP.h"
#include <cstdio>
#include <string>
#include <random>
#include <vector>
using namespace pipeline;

static void writeWav (const std::string& path, const std::vector<float>& x, int fs)
{
    FILE* f = std::fopen (path.c_str(), "wb");
    if (! f) return;
    const uint32_t n = (uint32_t) x.size(), bytes = n * 2;
    auto w32 = [&] (uint32_t v) { std::fwrite (&v, 4, 1, f); };
    auto w16 = [&] (uint16_t v) { std::fwrite (&v, 2, 1, f); };
    std::fwrite ("RIFF", 1, 4, f); w32 (36 + bytes); std::fwrite ("WAVEfmt ", 1, 8, f);
    w32 (16); w16 (1); w16 (1); w32 ((uint32_t) fs); w32 ((uint32_t) fs * 2); w16 (2); w16 (16);
    std::fwrite ("data", 1, 4, f); w32 (bytes);
    for (float v : x) { const int16_t s = (int16_t) std::lround (std::clamp (v, -1.0f, 1.0f) * 32767.0f); std::fwrite (&s, 2, 1, f); }
    std::fclose (f);
}

struct Pluck
{
    std::vector<float> d; int w = 0; float damp = 0.999f;
    void start (float fs, float hz, float amp, std::mt19937& rng)
    {
        d.assign ((size_t) std::lround (fs / hz - 0.5f), 0.0f);
        std::uniform_real_distribution<float> u (-amp, amp);
        float prev = 0; for (auto& v : d) { prev += 0.5f * (u (rng) - prev); v = prev; }
        damp = std::pow (0.001f, 1.0f / (6.0f * hz)); w = 0;
    }
    float tick()
    {
        if (d.empty()) return 0.0f;
        const int n = (int) d.size(); const float y = d[(size_t) w]; const int nx = (w + 1) % n;
        d[(size_t) w] = 0.5f * (y + d[(size_t) nx]) * damp; w = nx; return y;
    }
};

// hauteur instantanee d'une sinusoide traitee : periodes entre passages par zero (interpoles)
static void pitchStats (const std::vector<float>& y, int fs, float f0, int from, float& minC, float& maxC)
{
    minC = 1e9f; maxC = -1e9f;
    double last = -1.0;
    for (size_t i = (size_t) from + 1; i < y.size(); ++i)
        if (y[i - 1] < 0.0f && y[i] >= 0.0f)
        {
            const double t = (double) (i - 1) + y[i - 1] / (double) (y[i - 1] - y[i]);
            if (last > 0.0)
            {
                const double hz = fs / (t - last);
                const float c = (float) (1200.0 * std::log2 (hz / f0));
                minC = std::min (minC, c); maxC = std::max (maxC, c);
            }
            last = t;
        }
}

static const char* modeName[] = { "sine", "triangle", "ramp", "square", "random", "envd", "envr", "envp" };

int main (int argc, char** argv)
{
    const std::string out = argc > 1 ? argv[1] : ".";
    int fails = 0;
    for (int fs : { 44100, 48000, 96000 })
    {
        // 1) sinusoide 440 Hz : ecart de hauteur mesure pour quelques reglages
        for (int mode = 0; mode < 5; ++mode)
            for (float rate : { 0.2f, 0.5f, 0.8f, 1.0f })
                for (float depth : { 0.3f, 0.6f, 1.0f })
                {
                    Engine e; e.prepare (fs, 1);
                    Params p; p.mode = mode; p.rate = rate; p.depth = depth;
                    const int N = fs * 6;
                    std::vector<float> y ((size_t) N);
                    for (int i = 0; i < N; ++i) y[(size_t) i] = 0.25f * std::sin (2.0f * kPi * 440.0f * (float) i / (float) fs);
                    float* io[1] = { y.data() };
                    for (int i = 0; i < N; i += 256) { float* b[1] = { io[0] + i }; e.process (b, 1, std::min (256, N - i), p); }
                    float lo, hi; pitchStats (y, fs, 440.0f, fs, lo, hi);
                    bool bad = false;
                    for (float v : y) if (! std::isfinite (v) || std::abs (v) > 1.0f) bad = true;
                    if (bad || lo < -1300.0f || hi > 800.0f) ++fails;
                    if (fs == 48000)
                        std::printf ("%-8s rate %.1f (%5.2f Hz) depth %.1f : %+7.1f / %+7.1f cents%s\n", modeName[mode], rate,
                                     rateToHz (rate), depth, lo, hi, bad ? "  !! NON FINI / SATURE" : "");
                }

        // 2) guitare synthetique, tous les modes (WAV a 48 kHz)
        for (int mode = 0; mode < numModes; ++mode)
        {
            Engine e; e.prepare (fs, 2);
            Params p; p.mode = mode;
            p.rate = mode == EnvP ? 0.6f : (mode == EnvR ? 0.55f : 0.55f);
            p.depth = mode == EnvP ? 1.0f : (mode == EnvD ? 0.6f : 0.55f);
            std::mt19937 rng (5);
            Pluck s;
            const int N = fs * 10;
            std::vector<float> L ((size_t) N), R ((size_t) N), dry ((size_t) N);
            const float notes[] = { 82.41f, 196.0f, 329.63f, 49.0f, 246.94f };
            for (int i = 0; i < N; ++i)
            {
                if (i % (fs * 2) == fs / 10) s.start ((float) fs, notes[(i / (fs * 2)) % 5], (i / (fs * 2)) % 2 ? 0.45f : 0.18f, rng);
                dry[(size_t) i] = L[(size_t) i] = R[(size_t) i] = s.tick();
            }
            for (int i = 0; i < N; i += 512)
            {
                float* b[2] = { L.data() + i, R.data() + i };
                e.process (b, 2, std::min (512, N - i), p);
            }
            float peak = 0; bool bad = false;
            for (float v : L) { peak = std::max (peak, std::abs (v)); if (! std::isfinite (v)) bad = true; }
            if (bad || peak > 1.0f) ++fails;
            if (fs == 48000)
            {
                std::printf ("guitare %-8s : crete %.3f%s\n", modeName[mode], peak, bad ? "  !! NON FINI" : "");
                writeWav (out + "/pipeline_" + modeName[mode] + ".wav", L, fs);
                if (mode == 0) writeWav (out + "/pipeline_dry.wav", dry, fs);
            }
        }

        // 3) bypass : sortie = entree exacte apres le fondu
        {
            Engine e; e.prepare (fs, 1);
            Params p; p.active = false;
            std::vector<float> y ((size_t) fs), x ((size_t) fs);
            for (int i = 0; i < fs; ++i) x[(size_t) i] = y[(size_t) i] = 0.3f * std::sin (0.01f * (float) i);
            float* b[1] = { y.data() };
            e.process (b, 1, fs, p);
            double err = 0; for (int i = fs / 2; i < fs; ++i) err = std::max (err, (double) std::abs (y[(size_t) i] - x[(size_t) i]));
            if (err > 1e-6) { ++fails; std::printf ("bypass %d Hz : ecart %g !!\n", fs, err); }
        }
    }
    std::printf ("\n%s (%d echec(s))\n", fails == 0 ? "OK" : "ECHEC", fails);
    return fails == 0 ? 0 : 1;
}
