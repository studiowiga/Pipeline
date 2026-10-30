#include "PluginProcessor.h"
#include "PluginEditor.h"

using namespace juce;

//==============================================================================
// Presets d'usine - potards notes comme sur la pedale (0 a 10, 5 = 12 h)
// Les deux premiers reprennent les « Suggested Settings » du manuel d'origine.
//==============================================================================
static const PipelinePreset factoryPresets[] =
{
    //  nom                          rate  depth mode
    { "Smooth Sine Wave",            4.0f, 4.0f, 0 },   // manuel : « Smooth Sine Wave Modulation »
    { "Haunting Ramp (High Rate)",   7.5f, 5.0f, 2 },   // manuel : « Haunting Ramp at a High Rate »
    { "Chooglin' Amp Vibrato",       6.5f, 3.0f, 0 },   // vibrato d'ampli classique
    { "Seasick Sine",                2.5f, 7.5f, 0 },
    { "Triangle Wobble",             5.0f, 5.0f, 1 },
    { "Sonar Ping",                  3.5f, 6.5f, 2 },
    { "Hammer-On Trill",             6.5f, 6.0f, 3 },   // Square : trille sans hammer-on / pull-off
    { "Kosmische Pulse",             4.0f, 3.5f, 3 },
    { "Warped Record",               3.0f, 2.0f, 4 },   // Random a faible Depth
    { "Drunken Master",              5.0f, 8.5f, 4 },
    { "Motorik Dig-In",              6.0f, 6.0f, 5 },   // Env D : l'attaque fixe l'intensite
    { "Touch Rate Ripple",           5.5f, 4.5f, 6 },   // Env R : l'attaque fixe la vitesse
    { "My Bloody Valentine",         6.0f, 10.0f, 7 },  // Env P tout traite : le « vibrato de guitare »
    { "Touch Chorus",                3.0f, 5.0f, 7 },   // Env P a midi : 50/50
    { "Pseudo Flange",               1.5f, 5.0f, 7 },
};

int PipelineAudioProcessor::getNumFactoryPresets() { return (int) std::size (factoryPresets); }

const PipelinePreset& PipelineAudioProcessor::getFactoryPreset (int i)
{
    return factoryPresets[(size_t) jlimit (0, getNumFactoryPresets() - 1, i)];
}

const char* PipelineAudioProcessor::divisionName (int i)
{
    static const char* n[numDivisions] = { "4 BARS", "2 BARS", "1 BAR", "1/2", "1/4 D", "1/2 T", "1/4",
                                           "1/8 D", "1/4 T", "1/8", "1/8 T", "1/16", "1/16 T", "1/32" };
    return n[jlimit (0, numDivisions - 1, i)];
}

double PipelineAudioProcessor::divisionBeats (int i)
{
    static const double b[numDivisions] = { 16.0, 8.0, 4.0, 2.0, 1.5, 4.0 / 3.0, 1.0,
                                            0.75, 2.0 / 3.0, 0.5, 1.0 / 3.0, 0.25, 1.0 / 6.0, 0.125 };
    return b[jlimit (0, numDivisions - 1, i)];
}

const PipelineAudioProcessor::LearnDef& PipelineAudioProcessor::learnDef (int i)
{
    static const LearnDef defs[numLearn] =
    {
        { "rate",   "Rate",       ccRate,       learnContinuous, 0 },
        { "depth",  "Depth",      ccDepth,      learnContinuous, 0 },
        { "mode",   "Mode",       ccMode,       learnSelector,   8 },   // 0..127 -> 8 positions
        { "sync",   "Tempo Sync", ccSync,       learnToggle,     2 },   // >= 64 : ON
        { "active", "Footswitch", ccFootswitch, learnFootswitch, 0 },
    };
    return defs[jlimit (0, numLearn - 1, i)];
}

void PipelineAudioProcessor::resetMidiMap()
{
    for (int i = 0; i < numLearn; ++i) ccMap[i].store (learnDef (i).defaultCC);
}

//==============================================================================
PipelineAudioProcessor::PipelineAudioProcessor()
    : AudioProcessor (BusesProperties()
                        .withInput  ("Input",  AudioChannelSet::stereo(), true)
                        .withOutput ("Output", AudioChannelSet::stereo(), true)),
      apvts (*this, nullptr, "PIPELINE", createLayout())
{
    for (int i = 0; i < numRaw; ++i) rawPtr[i] = apvts.getRawParameterValue (rawIds[i]);
    for (int i = 0; i < numQueued; ++i) { pendingValue[i] = 0.0f; pendingSet[i] = false; }
    resetMidiMap();
    startTimerHz (60);
}

AudioProcessorValueTreeState::ParameterLayout PipelineAudioProcessor::createLayout()
{
    std::vector<std::unique_ptr<RangedAudioParameter>> p;
    const auto& d = factoryPresets[0];
    auto knob = [] (const String& id, const String& name, float def)
    {
        return std::make_unique<AudioParameterFloat> (
            ParameterID { id, 1 }, name, NormalisableRange<float> (0.0f, 10.0f, 0.01f), def,
            AudioParameterFloatAttributes().withStringFromValueFunction (
                [] (float v, int) { return String (roundToInt (v * 10.0f)) + " %"; }));
    };
    p.push_back (knob ("rate",  "Rate",  d.rate));
    p.push_back (knob ("depth", "Depth", d.depth));
    p.push_back (std::make_unique<AudioParameterChoice> (ParameterID { "mode", 1 }, "Mode",
                                                         StringArray { "Sine", "Triangle", "Ramp", "Square", "Random", "Env D", "Env R", "Env P" }, d.mode));
    p.push_back (std::make_unique<AudioParameterBool>   (ParameterID { "sync", 1 }, "Tempo Sync", false));
    p.push_back (std::make_unique<AudioParameterBool>   (ParameterID { "active", 1 }, "Footswitch", true));
    p.push_back (std::make_unique<AudioParameterBool>   (ParameterID { "flexi", 1 }, "Flexi-Switch (hold = momentary)", true));
    p.push_back (std::make_unique<AudioParameterChoice> (ParameterID { "midiFsMode", 1 }, "MIDI Footswitch Mode",
                                                         StringArray { "Toggle each press", "Latching (127 / 0)" }, 0));   // defaut : un appui = marche / arret
    return { p.begin(), p.end() };
}

bool PipelineAudioProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    const auto in = layouts.getMainInputChannelSet(), out = layouts.getMainOutputChannelSet();
    if (out != AudioChannelSet::mono() && out != AudioChannelSet::stereo()) return false;
    return in == out;
}

void PipelineAudioProcessor::setParamValue (const String& id, float plain)
{
    if (auto* prm = apvts.getParameter (id))
    {
        prm->beginChangeGesture();
        prm->setValueNotifyingHost (prm->convertTo0to1 (plain));
        prm->endChangeGesture();
    }
}

// Anti-gel : jamais d'appel a l'hote depuis le thread audio ; le MIDI met la valeur en file,
// un timer du thread de messages la transmet au DAW et a la fenetre.
const char* PipelineAudioProcessor::queuedId (int i)
{
    static const char* ids[numQueued] = { "rate", "depth", "mode", "sync", "active" };
    return ids[jlimit (0, numQueued - 1, i)];
}

void PipelineAudioProcessor::setParamFromAudio (int qi, float plain)
{
    pendingValue[qi].store (plain, std::memory_order_relaxed);
    pendingSet[qi].store (true, std::memory_order_release);
}

void PipelineAudioProcessor::timerCallback()
{
    for (int i = 0; i < numQueued; ++i)
        if (pendingSet[i].exchange (false, std::memory_order_acquire))
            if (auto* prm = apvts.getParameter (queuedId (i)))
                prm->setValueNotifyingHost (prm->convertTo0to1 (pendingValue[i].load (std::memory_order_relaxed)));
}

//==============================================================================
void PipelineAudioProcessor::prepareToPlay (double sampleRate, int)
{
    sr = sampleRate;
    engine.prepare (sr, jmax (1, getTotalNumOutputChannels()));
    for (auto& r : ramps) { r.active = false; r.left = 0; }
}

//==============================================================================
// MIDI
//==============================================================================
float PipelineAudioProcessor::mapCC (int k, float raw01)
{
    auto& r = ramps[k];
    if (raw01 < r.lo) r.lo = raw01;
    if (raw01 > r.hi) r.hi = raw01;
    float v = raw01;
    if (r.hi - r.lo > 0.4f) v = (raw01 - r.lo) / (r.hi - r.lo);   // course de la pedale apprise automatiquement
    constexpr float dz = 0.02f;                                     // zones mortes aux butees
    return jlimit (0.0f, 1.0f, (v - dz) / (1.0f - 2.0f * dz));
}

void PipelineAudioProcessor::handleMidi (MidiBuffer& midi)
{
    const bool latching = rawAt (rMidiFs) > 0.5f;    // par defaut (0) : chaque appui bascule marche / arret
    for (const auto meta : midi)
    {
        const auto m = meta.getMessage();
        const juce::int64 when = sampleClock + meta.samplePosition;
        if (m.isController())
        {
            const int cc = m.getControllerNumber(), v = m.getControllerValue();
            bool known = true;
            auto knobFromCC = [&] (int k, float raw01)
            {
                auto& r = ramps[k];
                const float target = mapCC (k, raw01) * 10.0f;
                if (! r.active) r.value = rawAt (k == 0 ? rRate : rDepth);
                const double interval = (double) (when - r.lastTime);
                r.left = (int) jlimit (0.002 * sr, 0.040 * sr, interval);
                r.lastTime = when;
                r.target = target;
                r.step = (r.target - r.value) / (float) r.left;
                r.active = true;
                setParamFromAudio (k, target);
                currentPreset = -1;
            };

            // MIDI Learn : le premier CC recu est affecte a la commande visee (il n'agit pas sur le son)
            const int lt = learnTarget.load();
            if (lt >= 0 && lt < numLearn && cc < 120)
            {
                for (int j = 0; j < numLearn; ++j)
                    if (j != lt && ccMap[j].load() == cc) ccMap[j].store (-1);
                ccMap[lt].store (cc);
                if (lt < numKnobs) ramps[lt].msb = -1;
                if (lt == 4) prevFsCC = v;
                lastLearned.store (lt);
                learnTarget.store (-1);
                lastMidiCC = cc; ++midiCounter;
                continue;
            }

            int ctl = -1;
            for (int j = 0; j < numLearn; ++j)
                if (ccMap[j].load (std::memory_order_relaxed) == cc) { ctl = j; break; }
            int lsbOf = -1;
            if (ctl < 0)
                for (int k = 0; k < numKnobs; ++k)
                {
                    const int msbCC = ccMap[k].load (std::memory_order_relaxed);
                    if (msbCC >= 0 && msbCC < 32 && cc == msbCC + 32) { lsbOf = k; break; }
                }

            if (ctl >= 0 && ctl < numKnobs)
            {
                ramps[ctl].msb = v;
                knobFromCC (ctl, (float) v / 127.0f);
            }
            else if (lsbOf >= 0)
            {
                // CC 14 bits (CC n + CC n+32) : resolution fine si la pedale l'envoie
                if (ramps[lsbOf].msb >= 0) knobFromCC (lsbOf, (float) (ramps[lsbOf].msb * 128 + v) / 16383.0f);
            }
            else if (ctl == 2) { setParamFromAudio (2, (float) jlimit (0, 7, v * 8 / 128)); currentPreset = -1; }
            else if (ctl == 3) { setParamFromAudio (3, v >= 64 ? 1.0f : 0.0f); }
            else if (ctl == 4)
            {
                // footswitch MIDI : a accrochage (127 = on / 0 = off, donc momentane avec un footswitch momentane)
                // ou bascule a chaque appui
                const float cur = pendingSet[4].load() ? pendingValue[4].load() : rawAt (rActive);
                if (latching)                       setParamFromAudio (4, v >= 64 ? 1.0f : 0.0f);
                else if (v >= 64 && prevFsCC < 64)  setParamFromAudio (4, cur > 0.5f ? 0.0f : 1.0f);
                prevFsCC = v;
            }
            else known = false;
            if (known) { lastMidiCC = cc; ++midiCounter; }
        }
        else if (m.isProgramChange())
        {
            const int pc = m.getProgramChangeNumber();
            if (pc < getNumFactoryPresets()) { pendingPreset = pc; triggerAsyncUpdate(); }
            lastMidiCC = -2; ++midiCounter;
        }
    }
    midi.clear();
}

void PipelineAudioProcessor::handleAsyncUpdate()
{
    const int p = pendingPreset.exchange (-1);
    if (p >= 0) applyFactoryPreset (p);
}

//==============================================================================
void PipelineAudioProcessor::processBlock (AudioBuffer<float>& buffer, MidiBuffer& midi)
{
    ScopedNoDenormals noDenormals;
    const int n = buffer.getNumSamples();
    handleMidi (midi);
    if (n == 0) return;
    for (int c = getTotalNumInputChannels(); c < getTotalNumOutputChannels(); ++c)
        buffer.clear (c, 0, n);

    float knobs[numKnobs];
    for (int k = 0; k < numKnobs; ++k)
    {
        auto& r = ramps[k];
        if (r.active)
        {
            const int adv = jmin (r.left, n);
            r.value += r.step * (float) adv;
            r.left -= adv;
            if (r.left <= 0) { r.value = r.target; r.active = false; }
            knobs[k] = r.value;
        }
        else knobs[k] = rawAt (k == 0 ? rRate : rDepth);
    }

    pipeline::Params p;
    p.rate  = knobs[0] / 10.0f;
    p.depth = knobs[1] / 10.0f;
    p.mode  = jlimit (0, 7, roundToInt (rawAt (rMode)));
    p.active = rawAt (rActive) > 0.5f;

    // synchro tempo du DAW (le potard RATE choisit la valeur de note)
    double bpm = 0.0, ppq = 0.0;
    bool playing = false, hasPpq = false;
    if (auto* ph = getPlayHead())
        if (auto pos = ph->getPosition())
        {
            if (auto b = pos->getBpm()) bpm = *b;
            if (auto q = pos->getPpqPosition()) { ppq = *q; hasPpq = true; }
            playing = pos->getIsPlaying();
        }
    hostBpm.store (bpm, std::memory_order_relaxed);
    if (rawAt (rSync) > 0.5f && bpm > 0.0)
    {
        const double beats = divisionBeats (divisionForRate (knobs[0]));
        p.syncHz = bpm / 60.0 / beats;
        if (playing && hasPpq)
        {
            const double cyc = ppq / beats;
            p.syncPhase = cyc - std::floor (cyc);
        }
    }

    const int nCh = jmin (2, buffer.getNumChannels());
    float* io[2] = { buffer.getWritePointer (0), nCh > 1 ? buffer.getWritePointer (1) : nullptr };
    engine.process (io, nCh, n, p);

    shownCents = engine.shownCents.load (std::memory_order_relaxed);
    shownEnv = engine.shownEnv.load (std::memory_order_relaxed);
    shownHz = p.syncHz > 0.0 ? (float) p.syncHz : pipeline::rateToHz (p.rate);
    sampleClock += n;
}

//==============================================================================
// Presets
//==============================================================================
int PipelineAudioProcessor::getCurrentProgram()
{
    const int c = currentPreset.load();
    return (c >= 0 && c < getNumFactoryPresets()) ? c : 0;
}

void PipelineAudioProcessor::applyFactoryPreset (int index)
{
    const auto& p = getFactoryPreset (index);
    setParamValue ("rate", p.rate);
    setParamValue ("depth", p.depth);
    setParamValue ("mode", (float) p.mode);
    currentPreset = jlimit (0, getNumFactoryPresets() - 1, index);
    ++presetCounter;
}

File PipelineAudioProcessor::getUserPresetFile()
{
    return File::getSpecialLocation (File::userApplicationDataDirectory)
             .getChildFile ("Studio Wiga").getChildFile ("Pipeline").getChildFile ("UserPresets.xml");
}

static const char* presetIds[] = { "rate", "depth", "mode", "sync" };

bool PipelineAudioProcessor::saveUserPreset (int slot)
{
    if (slot < 1 || slot > 9) return false;
    auto file = getUserPresetFile();
    file.getParentDirectory().createDirectory();
    std::unique_ptr<XmlElement> root;
    if (file.existsAsFile()) root = XmlDocument::parse (file);
    if (root == nullptr || ! root->hasTagName ("UserPresets")) root = std::make_unique<XmlElement> ("UserPresets");
    for (auto* e = root->getFirstChildElement(); e != nullptr; e = e->getNextElement())
        if (e->getIntAttribute ("slot") == slot) { root->removeChildElement (e, true); break; }
    auto* e = root->createNewChildElement ("Preset");
    e->setAttribute ("slot", slot);
    for (auto* id : presetIds) e->setAttribute (id, (double) raw (id));
    const bool ok = root->writeTo (file);
    if (ok) { currentPreset = 100 + slot; ++presetCounter; }
    return ok;
}

bool PipelineAudioProcessor::loadUserPreset (int slot)
{
    const auto file = getUserPresetFile();
    if (! file.existsAsFile()) return false;
    auto root = XmlDocument::parse (file);
    if (root == nullptr) return false;
    for (auto* e = root->getFirstChildElement(); e != nullptr; e = e->getNextElement())
        if (e->getIntAttribute ("slot") == slot)
        {
            for (auto* id : presetIds)
                if (e->hasAttribute (id)) setParamValue (id, (float) e->getDoubleAttribute (id));
            currentPreset = 100 + slot; ++presetCounter;
            return true;
        }
    return false;
}

bool PipelineAudioProcessor::hasUserPreset (int slot) const
{
    const auto file = getUserPresetFile();
    if (! file.existsAsFile()) return false;
    if (auto root = XmlDocument::parse (file))
        for (auto* e = root->getFirstChildElement(); e != nullptr; e = e->getNextElement())
            if (e->getIntAttribute ("slot") == slot) return true;
    return false;
}

//==============================================================================
void PipelineAudioProcessor::getStateInformation (MemoryBlock& dest)
{
    auto state = apvts.copyState();
    state.setProperty ("currentPreset", currentPreset.load(), nullptr);
    for (int i = 0; i < numLearn; ++i)
        state.setProperty (String ("cc_") + learnDef (i).id, ccMap[i].load(), nullptr);
    if (auto xml = state.createXml()) copyXmlToBinary (*xml, dest);
}

void PipelineAudioProcessor::setStateInformation (const void* data, int size)
{
    if (auto xml = getXmlFromBinary (data, size))
        if (xml->hasTagName (apvts.state.getType()))
        {
            auto state = ValueTree::fromXml (*xml);
            currentPreset = (int) state.getProperty ("currentPreset", 0);
            for (int i = 0; i < numLearn; ++i)
                ccMap[i].store (jlimit (-1, 127, (int) state.getProperty (String ("cc_") + learnDef (i).id, learnDef (i).defaultCC)));
            apvts.replaceState (state);
            ++presetCounter;
        }
}

//==============================================================================
AudioProcessorEditor* PipelineAudioProcessor::createEditor() { return new PipelineAudioProcessorEditor (*this); }

AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new PipelineAudioProcessor(); }
