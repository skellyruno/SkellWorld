#pragma once
#include <JuceHeader.h>
#include <SkellCore/WorldLink.h>
class SkellAudioProcessor final : public juce::AudioProcessor {
public:
  SkellAudioProcessor();
  void prepareToPlay(double sampleRate, int) override;
  void releaseResources() override {}
  bool isBusesLayoutSupported(const BusesLayout& l) const override;
  void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
  juce::AudioProcessorEditor* createEditor() override;
  bool hasEditor() const override { return true; }
  const juce::String getName() const override { return "Skell Quickstart"; }
  bool acceptsMidi() const override { return false; }
  bool producesMidi() const override { return false; }
  bool isMidiEffect() const override { return false; }
  double getTailLengthSeconds() const override { return 0.0; }
  int getNumPrograms() override { return 1; }
  int getCurrentProgram() override { return 0; }
  void setCurrentProgram(int) override {}
  const juce::String getProgramName(int) override { return {}; }
  void changeProgramName(int, const juce::String&) override {}
  void getStateInformation(juce::MemoryBlock&) override;
  void setStateInformation(const void*, int) override;
  // Persists for the plugin instance, even if its editor closes.
  // No connection is attempted unless the user explicitly joins.
  skellcore::world::WorldLink worldLink{"skellcore.quickstart", "Skell Quickstart"};
  juce::AudioProcessorValueTreeState parameters;
  static juce::AudioProcessorValueTreeState::ParameterLayout createLayout();
private:
  juce::SmoothedValue<float, juce::ValueSmoothingTypes::Linear> smoothedGain_{1.0f};
  JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(SkellAudioProcessor)
};
