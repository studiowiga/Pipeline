// genere par tools/make_background.py - ne pas modifier a la main (repere 760 x 958)
#pragma once
#include <juce_graphics/juce_graphics.h>
namespace layout
{
    const juce::Point<float> ratePos { 262.00f, 196.00f }, depthPos { 498.00f, 196.00f }, modePos { 380.00f, 390.00f };
    const float knobTop = 37.00f, knobSkirt = 50.00f, modeTop = 27.00f, modeSkirt = 35.00f;
    const float modeFirstDeg = -150.0000f, modeStepDeg = 42.8571f;     // 8 positions
    const juce::Point<float> ledPos { 380.00f, 748.00f }, footPos { 380.00f, 828.00f };
    const float footR = 44.0f, ledLensR = 6.20f;
    const juce::Rectangle<float> glowRect { 265.00f, 633.00f, 230.00f, 230.00f };
    const juce::Rectangle<float> rowRect { 204.00f, 614.00f, 352.00f, 48.00f };
    const juce::Rectangle<float> barRect { 212.00f, 670.00f, 336.00f, 32.00f };
}
