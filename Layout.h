// genere par tools/make_background.py - ne pas modifier a la main (repere 760 x 958)
#pragma once
#include <juce_graphics/juce_graphics.h>
namespace layout
{
    const juce::Point<float> ratePos { 246.08f, 210.04f }, depthPos { 515.45f, 210.04f }, modePos { 380.77f, 403.98f };
    const float knobTop = 39.52f, knobSkirt = 52.69f, modeTop = 25.61f, modeSkirt = 36.59f;
    const float modeFirstDeg = -150.0000f, modeStepDeg = 42.8571f;     // 8 positions
    const juce::Point<float> ledPos { 380.00f, 68.06f }, footPos { 380.38f, 863.59f };
    const float footR = 54.16f, ledLensR = 6.59f;
    const juce::Rectangle<float> glowRect { 313.00f, 1.00f, 134.00f, 134.00f };
    const juce::Rectangle<float> rowRect { 182.57f, 652.08f, 397.93f, 49.77f };
    const juce::Rectangle<float> barRect { 188.69f, 707.71f, 382.62f, 35.13f };
}
