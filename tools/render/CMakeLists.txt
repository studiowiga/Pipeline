# Outil hors plugin : compile le processeur + la fenetre de Pipeline sous Linux et exporte des captures PNG (apercu, notice)
cmake_minimum_required(VERSION 3.22)
project(PipelineRender VERSION 1.4.1)
set(CMAKE_CXX_STANDARD 17)
add_subdirectory(${JUCE_DIR} JUCE)
set(W ${CMAKE_CURRENT_SOURCE_DIR}/../..)
juce_add_binary_data(PipelineAssets SOURCES
  ${W}/background.jpg ${W}/glow_led.png ${W}/knob_strip.png ${W}/mode_labels.png
  ${W}/assets/fonts/BarlowCondensed-SemiBold.ttf ${W}/assets/fonts/BarlowCondensed-Bold.ttf)
juce_add_console_app(PipelineRender PRODUCT_NAME "PipelineRender")
target_sources(PipelineRender PRIVATE main.cpp ${W}/PluginProcessor.cpp ${W}/PluginEditor.cpp)
target_include_directories(PipelineRender PRIVATE ${W})
target_compile_definitions(PipelineRender PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_ALSA=0 JUCE_JACK=0
  JUCE_USE_XRANDR=0 JUCE_USE_XINERAMA=0 JUCE_USE_XCURSOR=0 JucePlugin_Name="Pipeline" JucePlugin_Build_VST3=0
  JucePlugin_VersionString="1.4.1" JUCE_STANDALONE_APPLICATION=1 JUCE_MODAL_LOOPS_PERMITTED=1)
target_link_libraries(PipelineRender PRIVATE PipelineAssets juce::juce_audio_utils juce::juce_recommended_config_flags)
