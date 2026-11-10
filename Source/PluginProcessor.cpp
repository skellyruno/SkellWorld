#include <SkellCore/Core.h>
#include "PluginProcessor.h"
#include "PluginEditor.h"
#include <cmath>
SkellAudioProcessor::SkellAudioProcessor()
 : AudioProcessor(BusesProperties().withInput("Input",juce::AudioChannelSet::stereo(),true).withOutput("Output",juce::AudioChannelSet::stereo(),true)),
   parameters(*this,nullptr,"PARAMETERS",createLayout()) {}
juce::AudioProcessorValueTreeState::ParameterLayout SkellAudioProcessor::createLayout() {
  juce::AudioProcessorValueTreeState::ParameterLayout layout;
  layout.add(std::make_unique<juce::AudioParameterFloat>(juce::ParameterID{"gain",1},"Gain",juce::NormalisableRange<float>(0.0f,2.0f,0.001f),1.0f));
  return layout;
}
bool SkellAudioProcessor::isBusesLayoutSupported(const BusesLayout& l) const {
  auto input=l.getMainInputChannelSet();
  return (input==juce::AudioChannelSet::mono() || input==juce::AudioChannelSet::stereo()) && input==l.getMainOutputChannelSet();
}
void SkellAudioProcessor::prepareToPlay(double sampleRate, int) {
  // 15 ms gain smoothing avoids clicks from DAW automation.
  const auto safeRate = std::isfinite(sampleRate) ? juce::jlimit(1000.0, 192000.0, sampleRate) : 48000.0;
  smoothedGain_.reset(safeRate, 0.015);
  const auto* raw = parameters.getRawParameterValue("gain");
  const float initial = raw ? raw->load() : 1.0f;
  smoothedGain_.setCurrentAndTargetValue(std::isfinite(initial) ? juce::jlimit(0.0f, 2.0f, initial) : 1.0f);
}
void SkellAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer&) {
  juce::ScopedNoDenormals guard;
  const int frames = buffer.getNumSamples();
  if (frames <= 0) return;
  const auto* raw = parameters.getRawParameterValue("gain");
  const float requested = raw ? raw->load() : 1.0f;
  const float target = std::isfinite(requested) ? juce::jlimit(0.0f, 2.0f, requested) : 1.0f;
  smoothedGain_.setTargetValue(target);
  if (!smoothedGain_.isSmoothing()) {
    buffer.applyGain(target);
  } else {
    const auto initial = smoothedGain_.getCurrentValue();
    const auto end = smoothedGain_.skip(frames);
    buffer.applyGainRamp(0, frames, initial, end);
  }
}
juce::AudioProcessorEditor* SkellAudioProcessor::createEditor() { return new SkellAudioProcessorEditor(*this); }
void SkellAudioProcessor::getStateInformation(juce::MemoryBlock& dest) {
  if(auto xml=parameters.copyState().createXml()) copyXmlToBinary(*xml,dest);
}
void SkellAudioProcessor::setStateInformation(const void* data,int size) {
  if(auto xml=getXmlFromBinary(data,size))
    if(xml->hasTagName(parameters.state.getType())) parameters.replaceState(juce::ValueTree::fromXml(*xml));
}
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new SkellAudioProcessor(); }
