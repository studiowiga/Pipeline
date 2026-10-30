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
    // etiquettes du selecteur allumees (mode_labels.png : 8 images 135 x 73 px du fond 2x empilees)
    const float labelW = 67.50f, labelH = 36.50f;
    const juce::Point<float> labelPos[8] = { { 336.75f, 481.75f }, { 290.75f, 435.75f }, { 296.75f, 370.25f }, { 348.75f, 331.25f }, { 412.25f, 331.25f }, { 465.75f, 370.25f }, { 470.75f, 435.75f }, { 424.25f, 481.75f } };
}
