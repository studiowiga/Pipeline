// genere par tools/make_background.py - ne pas modifier a la main (repere 760 x 958)
#pragma once
#include <juce_graphics/juce_graphics.h>
namespace layout
{
    const juce::Point<float> ratePos { 244.25f, 212.97f }, depthPos { 517.30f, 212.97f }, modePos { 380.78f, 409.62f };
    const float knobTop = 40.07f, knobSkirt = 53.43f, modeTop = 25.97f, modeSkirt = 37.10f;
    const float modeFirstDeg = -150.0000f, modeStepDeg = 42.8571f;     // 8 positions
    const juce::Point<float> ledPos { 380.00f, 69.01f }, footPos { 380.78f, 840.75f };
    const float footR = 50.52f, ledLensR = 6.68f;
    const juce::Rectangle<float> glowRect { 312.00f, 1.00f, 136.00f, 136.00f };
    const juce::Rectangle<float> rowRect { 179.87f, 661.18f, 403.37f, 50.46f };
    const juce::Rectangle<float> barRect { 186.07f, 717.57f, 387.85f, 35.62f };
}
