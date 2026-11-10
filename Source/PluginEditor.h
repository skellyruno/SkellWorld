#pragma once
#include <JuceHeader.h>
#include "PluginProcessor.h"
#include <SkellCore/UI.h>
#include <SkellCore/WorldLink.h>
class SkellAudioProcessorEditor final : public juce::AudioProcessorEditor, private juce::Timer {
public:
  explicit SkellAudioProcessorEditor(SkellAudioProcessor&);
  ~SkellAudioProcessorEditor() override;
  void paint(juce::Graphics&) override;
  void resized() override;
private:
  void timerCallback() override;
  skellcore::ui::LookAndFeel skin_;
  skellcore::world::WorldLink& world_;
  juce::TextButton worldButton_{"JOIN WORLD"};
  juce::Label worldStatus_;
  juce::Slider gain;
  juce::Label title;
  juce::AudioProcessorValueTreeState::SliderAttachment gainAttachment;
  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(SkellAudioProcessorEditor)
};
