// Smoke test: capture the template's real JUCE AudioProcessorEditor.
#include "../Source/PluginProcessor.h"
#include "../Source/PluginEditor.h"
#include <SkellCore/HeadlessUIRenderer.h>
#include <JuceHeader.h>
#include <cstdio>

int main(int argc, char** argv) {
    juce::ScopedJuceInitialiser_GUI juceGui;
    SkellAudioProcessor processor;
    processor.prepareToPlay(48000.0, 512);
    SkellAudioProcessorEditor editor(processor);
    skellcore::ui::headless::Options options;
    options.project = "SkellCore template quickstart";
    options.scenes = {{"quickstart_small", 390, 250},
                      {"quickstart_default", 480, 330},
                      {"quickstart_large", 840, 560}};
    options.inspect = [&editor] {
        juce::StringArray problems;
        for (int i = 0; i < editor.getNumChildComponents(); ++i) {
            const auto* child = editor.getChildComponent(i);
            if (child->isVisible() && !editor.getLocalBounds().contains(child->getBounds()))
                problems.add("Visible control extends outside window: " + child->getName());
        }
        return problems;
    };
    const auto directory = argc > 1
        ? juce::File::getCurrentWorkingDirectory().getChildFile(juce::String::fromUTF8(argv[1]))
        : juce::File::getCurrentWorkingDirectory().getChildFile("ui-screenshots");
    const auto report = skellcore::ui::headless::render(editor, directory, options);
    for (const auto& error : report.errors)
        std::fprintf(stderr, "%s\n", error.toRawUTF8());
    std::printf("Captured %d / %zu SkellCore template scenes\n",
                report.captured, options.scenes.size());
    processor.releaseResources();
    return report.passed() && report.captured == static_cast<int>(options.scenes.size()) ? 0 : 1;
}
