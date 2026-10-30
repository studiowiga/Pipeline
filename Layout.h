// genere par tools/make_background.py - ne pas modifier a la main (repere 760 x 958)
#pragma once
#include <juce_graphics/juce_graphics.h>
namespace layout
{
    const juce::Point<float> ratePos { 241.27f, 217.69f }, depthPos { 520.31f, 217.69f }, modePos { 380.79f, 418.70f };
    const float knobTop = 40.96f, knobSkirt = 54.61f, modeTop = 26.55f, modeSkirt = 37.93f;
    const float modeFirstDeg = -150.0000f, modeStepDeg = 42.8571f;     // 8 positions
    const juce::Point<float> ledPos { 380.00f, 70.54f }, footPos { 380.40f, 860.15f };
    const float footR = 56.13f, ledLensR = 6.83f;
    const juce::Rectangle<float> glowRect { 310.50f, 1.00f, 139.00f, 139.00f };
    const juce::Rectangle<float> rowRect { 175.47f, 675.83f, 412.22f, 51.58f };
    const juce::Rectangle<float> barRect { 181.82f, 733.48f, 396.37f, 36.41f };
}
