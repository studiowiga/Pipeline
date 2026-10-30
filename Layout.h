// genere par tools/make_background.py - ne pas modifier a la main (repere 760 x 958)
#pragma once
#include <juce_graphics/juce_graphics.h>
namespace layout
{
    const juce::Point<float> ratePos { 244.25f, 212.97f }, depthPos { 517.30f, 212.97f }, modePos { 380.78f, 409.62f };
    const float knobTop = 40.07f, knobSkirt = 53.43f, modeTop = 25.97f, modeSkirt = 37.10f;
    const float modeFirstDeg = -150.0000f, modeStepDeg = 42.8571f;     // 8 positions
    const juce::Point<float> ledPos { 380.00f, 69.01f }, footPos { 380.78f, 840.75f };
    const float footR = 50.52f, ledLensR = 9.65f;
    const juce::Rectangle<float> glowRect { 312.00f, 1.00f, 136.00f, 136.00f };
    const juce::Rectangle<float> rowRect { 179.87f, 661.18f, 403.37f, 50.46f };
    const juce::Rectangle<float> barRect { 186.07f, 717.57f, 387.85f, 35.62f };
    // etiquettes du selecteur allumees (mode_labels.png : 8 images 110 x 62 px du fond 2x empilees)
    const float labelW = 55.00f, labelH = 31.00f;
    const juce::Point<float> labelPos[8] = { { 339.00f, 478.50f }, { 294.50f, 435.00f }, { 300.00f, 372.00f }, { 350.00f, 334.50f }, { 410.50f, 334.50f }, { 462.00f, 372.00f }, { 467.00f, 435.00f }, { 422.50f, 478.50f } };
}
