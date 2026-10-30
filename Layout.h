// genere par tools/make_background.py - ne pas modifier a la main (repere 760 x 958)
#pragma once
#include <juce_graphics/juce_graphics.h>
namespace layout
{
    const juce::Point<float> ratePos { 256.70f, 220.71f }, depthPos { 503.20f, 220.71f }, modePos { 380.29f, 419.15f };
    const float knobTop = 34.70f, knobSkirt = 51.08f, modeTop = 25.54f, modeSkirt = 36.62f;
    const float modeFirstDeg = -150.0000f, modeStepDeg = 42.8571f;     // 8 positions
    const juce::Point<float> ledPos { 380.48f, 113.73f }, footPos { 380.48f, 820.18f };
    const float footR = 40.79f, ledLensR = 6.30f;
    const juce::Rectangle<float> glowRect { 270.50f, 3.50f, 220.00f, 220.00f };
    const juce::Rectangle<float> rowRect { 203.24f, 649.59f, 354.47f, 36.62f };
    const juce::Rectangle<float> barRect { 206.13f, 700.96f, 349.95f, 31.52f };
}
