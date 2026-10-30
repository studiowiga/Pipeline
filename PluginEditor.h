#pragma once

#include "PluginProcessor.h"
#include <juce_gui_basics/juce_gui_basics.h>

//==============================================================================
// Potard RATE / DEPTH : le corps (et ses reflets) fait partie du fond, seul le repere peint tourne.
//==============================================================================
class PedalKnob : public juce::Component
{
public:
    explicit PedalKnob (juce::RangedAudioParameter& p);
    void paint (juce::Graphics&) override {}
    bool hitTest (int x, int y) override;
    void mouseDown (const juce::MouseEvent&) override;
    void mouseDrag (const juce::MouseEvent&) override;
    void mouseUp (const juce::MouseEvent&) override;
    void mouseDoubleClick (const juce::MouseEvent&) override;
    void mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails&) override;
    float getValue() const { return value; }
    bool isDragging() const { return dragging; }
    std::function<void()> onRightClick, onUserChange;

private:
    void setV (float v);
    juce::ParameterAttachment attachment;
    float value = 5.0f, startV = 5.0f;
    bool dragging = false;
};

//==============================================================================
// Selecteur MODE a 8 positions (crans de 42,9 degres), rotation animee ; clic sur une etiquette = cette position
//==============================================================================
class ModeKnob : public juce::Component
{
public:
    explicit ModeKnob (juce::RangedAudioParameter& p);
    void paint (juce::Graphics&) override {}
    bool hitTest (int x, int y) override;
    void mouseDown (const juce::MouseEvent&) override;
    void mouseDrag (const juce::MouseEvent&) override;
    void mouseUp (const juce::MouseEvent&) override;
    void mouseWheelMove (const juce::MouseEvent&, const juce::MouseWheelDetails&) override;
    bool tick();
    void moveTo (int p);
    float getShownAngle() const { return shownAngle; }
    int getPosition() const { return pos; }
    std::function<void()> onRightClick, onUserChange;

private:
    juce::ParameterAttachment attachment;
    int pos = 0, dragStartPos = 0;
    float shownAngle = 0.0f, targetAngle = 0.0f;
    // crans (butees) : le repere resiste un peu puis « tombe » dans le cran suivant avec un leger rebond
    float lean = 0.0f, velocity = 0.0f;
    bool dragging = false;
};

//==============================================================================
// Footswitch (reference Echoflex) : bascule des l'appui, bouton assombri tant qu'on appuie.
// Flexi-Switch (comme l'Aqueduct) : appui maintenu (> 0,45 s) quand l'effet etait coupe = momentane.
//==============================================================================
class FootSwitchArea : public juce::Component
{
public:
    FootSwitchArea (juce::RangedAudioParameter& active, std::atomic<float>* flexi);
    void paint (juce::Graphics&) override {}
    void mouseDown (const juce::MouseEvent&) override;
    void mouseUp (const juce::MouseEvent&) override;
    bool hitTest (int x, int y) override;
    bool isPressed() const { return pressed; }
    std::function<void()> onRightClick, onUserChange, onPressChange;

private:
    bool value = false, pressed = false, turnedOnByPress = false;
    double downTime = 0.0;
    std::atomic<float>* flexi = nullptr;
    juce::ParameterAttachment attachment;
};

//==============================================================================
struct PipelineLookAndFeel : public juce::LookAndFeel_V4
{
    void drawCornerResizer (juce::Graphics& g, int w, int h, bool over, bool dragging) override
    {
        const float a = dragging ? 0.55f : (over ? 0.38f : 0.16f);
        g.setColour (juce::Colours::white.withAlpha (a));
        const float s = (float) juce::jmin (w, h);
        for (float k : { 0.30f, 0.58f, 0.86f })
            g.drawLine (s * (1.0f - k), s - 1.0f, s - 1.0f, s * (1.0f - k), 1.0f);
    }
};

//==============================================================================
class PipelineAudioProcessorEditor : public juce::AudioProcessorEditor,
                                     private juce::Timer
{
public:
    explicit PipelineAudioProcessorEditor (PipelineAudioProcessor&);
    ~PipelineAudioProcessorEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;
    void parentHierarchyChanged() override;
    void mouseDown (const juce::MouseEvent&) override;
    void mouseMove (const juce::MouseEvent&) override;
    void mouseExit (const juce::MouseEvent&) override;

    // repere de reference (100 %) et taille par defaut = taille minimale (identique a Echoflex)
    static constexpr int baseW = 760;
    static constexpr int baseH = 958;
    static constexpr int defaultH = 493;

    void setScaledHeight (int h);
    void showStatus();

private:
    void timerCallback() override;
    void useSoftwareRenderer();
    void visibilityChanged() override;
    void askRepaint (juce::Rectangle<int> r);
    void showContextMenu (int learnIdx = -1);
    void addMidiMenu (juce::PopupMenu& menu, int learnIdx);
    void handleMidiMenu (int r);
    void showPresetMenu();
    void stepPreset (int delta);
    void rebuildCaches (float scale = 0.0f);
    float physicalScale() const;
    juce::Rectangle<int> scaled (juce::Rectangle<float> r) const;
    juce::String rateText (float v) const;
    juce::String buildStatusLine() const;
    juce::String buildInfoLine() const;
    juce::String buildPresetLine() const;
    int modeLabelAt (juce::Point<float> unitPos) const;
    void drawLed (juce::Graphics&);
    void drawKnobs (juce::Graphics&);
    void drawFootswitch (juce::Graphics&);
    void drawDisplay (juce::Graphics&);
    juce::Font presetFont (float availW);
    float presetFontAvail = -1.0f, presetFontH = 22.0f;

    PipelineAudioProcessor& proc;
    PipelineLookAndFeel lnf;

    juce::Image background, bgScaled, glowLed, glowLedS;
    // potards moletes de Holyverb : filmstrip 8 phases du moletage (lumiere fixe en haut a gauche), copies a l'echelle
    juce::Image knobStrip, knobBig, knobSmall;
    // etiquettes du selecteur allumees en bleu (ecriture LED) : 8 images empilees, fondu a l'allumage / extinction
    juce::Image labelStrip, labelStripS;
    float labelLit[8] {}, drawnLabel[8] { -1, -1, -1, -1, -1, -1, -1, -1 };
    void drawModeLabels (juce::Graphics&);
    int cacheW = 0, cacheH = 0;
    float cacheScale = 0.0f;
    int resizeSettle = 0;
    void* lastPeer = nullptr;
    double lastPaintMs = 0.0, repaintAskedMs = 0.0, lastScaleCheckMs = 0.0, lastRendererCheckMs = 0.0;
    juce::Typeface::Ptr labelFace, boldFace;

    PedalKnob rateKnob, depthKnob;
    ModeKnob modeKnob;
    FootSwitchArea foot;

    // animation
    float ledLevel = 0.0f, drawnLed = -1.0f;
    float drawnKnob[2] { -1.0f, -1.0f };
    int lastChanged = -1;
    float statusAlpha = 0.0f, drawnStatus = -1.0f;
    double statusUntil = 0.0;
    juce::String lastLine1, lastInfo, lastPreset;
    float lastValues[8];
    int lastPresetCounter = 0, lastMidiCount = 0, midiFlash = 0;
    int hoverZone = 0, drawnHover = -1;
    float peakCents = 0.0f;              // ecart de hauteur crete (affichage, retombe doucement)
    // oscilloscope de l'ecran : forme de la modulation de hauteur (mode, vitesse, profondeur), defile en temps reel
    static constexpr int histN = 64;     // 64 images a 30 Hz = ~2,1 s
    float envHist[histN] {}, centsHist[histN] {};
    int histPos = 0;
    double scopePhase = 0.0, lastScopeMs = 0.0;
    bool scopeWasLive = true;
    void drawScope (juce::Graphics&, juce::Rectangle<float>);
    double infoNextMs = 0.0;

    juce::String learnLine;
    double learnLineUntil = 0.0;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (PipelineAudioProcessorEditor)
};
