#pragma once
#include <cstring>

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_audio_utils/juce_audio_utils.h>
#include <atomic>
#include "PipelineDSP.h"

//==============================================================================
// PIPELINE (Studio Wiga) - vibrato de hauteur a 8 modes, d'apres l'EarthQuaker Devices Aqueduct.
// Voir README.md et PipelineDSP.h.
//==============================================================================

struct PipelinePreset
{
    const char* name;
    float rate, depth;      // 0..10 comme sur la pedale (5 = 12 h)
    int   mode;             // 0 Sine, 1 Triangle, 2 Ramp, 3 Square, 4 Random, 5 Env D, 6 Env R, 7 Env P
};

class PipelineAudioProcessor : public juce::AudioProcessor,
                               private juce::AsyncUpdater,
                               private juce::Timer
{
public:
    PipelineAudioProcessor();
    ~PipelineAudioProcessor() override = default;

    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override {}
    bool isBusesLayoutSupported (const BusesLayout&) const override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    using AudioProcessor::processBlock;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }
    const juce::String getName() const override { return "Pipeline"; }
    bool acceptsMidi() const override  { return true; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.1; }

    static int getNumFactoryPresets();
    static const PipelinePreset& getFactoryPreset (int index);
    int getNumPrograms() override { return getNumFactoryPresets(); }
    int getCurrentProgram() override;
    void setCurrentProgram (int index) override { applyFactoryPreset (index); }
    const juce::String getProgramName (int index) override { return getFactoryPreset (index).name; }
    void changeProgramName (int, const juce::String&) override {}
    void applyFactoryPreset (int index);

    bool saveUserPreset (int slot);
    bool loadUserPreset (int slot);
    bool hasUserPreset (int slot) const;
    static juce::File getUserPresetFile();

    void getStateInformation (juce::MemoryBlock&) override;
    void setStateInformation (const void*, int) override;

    juce::AudioProcessorValueTreeState apvts;
    static juce::AudioProcessorValueTreeState::ParameterLayout createLayout();
    void setParamValue (const juce::String& id, float plain);

    // anti-gel : pointeurs des parametres mis en cache au demarrage (aucune recherche par chaine dans processBlock)
    enum RawIndex { rRate, rDepth, rMode, rSync, rActive, rFlexi, rMidiFs, numRaw };
    static constexpr const char* rawIds[numRaw] = { "rate", "depth", "mode", "sync", "active", "flexi", "midiFsMode" };
    std::atomic<float>* rawPtr[numRaw] {};
    float rawAt (int i) const { return rawPtr[i]->load (std::memory_order_relaxed); }
    float raw (const char* id) const
    {
        for (int i = 0; i < numRaw; ++i)
            if (std::strcmp (id, rawIds[i]) == 0) return rawAt (i);
        return apvts.getRawParameterValue (id)->load();
    }

    static juce::StringArray modeNames()      { return { "SINE", "TRIANGLE", "RAMP", "SQUARE", "RANDOM", "ENV D", "ENV R", "ENV P" }; }
    static juce::StringArray modeShortNames() { return { "SINE", "TRI", "RAMP", "SQR", "RAND", "ENV D", "ENV R", "ENV P" }; }

    // synchro tempo : le potard RATE choisit une valeur de note (un cycle de LFO)
    static constexpr int numDivisions = 14;
    static const char* divisionName (int i);
    static double divisionBeats (int i);           // noires par cycle
    static int divisionForRate (float rate0to10) { return juce::jlimit (0, numDivisions - 1, juce::roundToInt (rate0to10 / 10.0f * (float) (numDivisions - 1))); }

    // ---- informations pour la fenetre ----
    std::atomic<int>   currentPreset { 0 };
    std::atomic<int>   presetCounter { 0 };
    std::atomic<int>   lastMidiCC { -1 }, midiCounter { 0 };
    std::atomic<float> shownCents { 0.0f };       // ecart de hauteur instantane
    std::atomic<float> shownEnv { 0.0f };         // enveloppe (modes Env)
    std::atomic<float> shownHz { 0.0f };          // vitesse du LFO en cours
    std::atomic<double> hostBpm { 0.0 };          // tempo du DAW (0 = inconnu)

    enum MidiMap
    {
        ccRate = 20, ccDepth = 21,
        ccMode = 22,        // 0..127 -> 8 positions
        ccSync = 23,        // >= 64 : synchro tempo
        ccFootswitch = 24   // footswitch (effet on / off)
    };
    static constexpr int numKnobs = 2;
    static const char* knobId (int i) { return i == 0 ? "rate" : "depth"; }

    // MIDI Learn : toutes les commandes de la facade (meme ordre que la file anti-gel queuedId)
    enum LearnType { learnContinuous, learnToggle, learnSelector, learnFootswitch };
    struct LearnDef { const char* id; const char* name; int defaultCC; int type; int positions; };
    static constexpr int numLearn = 5;
    static const LearnDef& learnDef (int i);
    std::atomic<int> ccMap[numLearn];
    std::atomic<int> learnTarget { -1 };
    std::atomic<int> lastLearned { -1 };
    void resetMidiMap();

private:
    void handleMidi (juce::MidiBuffer& midi);
    void setParamFromAudio (int queueIndex, float plain);
    void timerCallback() override;
    static constexpr int numQueued = 5;      // rate, depth, mode, sync, active
    static const char* queuedId (int i);
    std::atomic<float> pendingValue[numQueued];
    std::atomic<bool>  pendingSet[numQueued];
    void handleAsyncUpdate() override;
    float mapCC (int knob, float raw01);

    pipeline::Engine engine;
    double sr = 48000.0;

    struct ExprRamp
    {
        bool  active = false;
        float value = 0.0f, target = 0.0f, step = 0.0f;
        int   left = 0;
        juce::int64 lastTime = 0;
        int   msb = -1;
        float lo = 1.0f, hi = 0.0f;
    } ramps[numKnobs];
    juce::int64 sampleClock = 0;
    int prevFsCC = 0;
    std::atomic<int> pendingPreset { -1 };

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (PipelineAudioProcessor)
};
