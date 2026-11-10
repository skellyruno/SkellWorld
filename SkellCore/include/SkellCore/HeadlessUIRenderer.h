#pragma once
// SkellCore real-editor screenshot harness (JUCE 7+, C++17).
// Run on the JUCE message thread. Linux requires Xvfb or another display.
#include <juce_core/juce_core.h>
#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_graphics/juce_graphics.h>
#include <algorithm>
#include <cstdint>
#include <functional>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace skellcore::ui::headless {

struct Scene {
    juce::String id;   // Filename stem: letters, digits, '_' and '-'.
    int width = 0, height = 0;
    int theme = 0, mode = 0;
    bool browser = false;
};

struct Options {
    juce::String project = "JUCE editor";
    std::vector<Scene> scenes;
    std::function<void(const Scene&)> configure;
    std::function<juce::StringArray()> inspect;
    std::vector<std::pair<juce::String, juce::String>> mustDiffer;
    int minimumColours = 12;
};

struct Report {
    int captured = 0;
    juce::StringArray errors;
    bool passed() const noexcept { return errors.isEmpty(); }
};

inline bool writePng(const juce::Image& image, const juce::File& file) {
    if (!image.isValid()) return false;
    juce::FileOutputStream stream(file);
    if (!stream.openedOk()) return false;
    juce::PNGImageFormat format;
    const bool ok = format.writeImageToStream(image, stream);
    stream.flush();
    return ok && file.getSize() > 1024;
}

struct Capture {
    juce::Image image;
    std::uint64_t fingerprint = 14695981039346656037ull;
    int distinctColours = 0;
};

inline Capture capture(juce::Component& editor, int width, int height) {
    Capture result;
    if (width < 1 || height < 1) return result;
    editor.setSize(width, height);
    result.image = editor.createComponentSnapshot(editor.getLocalBounds(), true);
    if (!result.image.isValid() || result.image.getWidth() != width
        || result.image.getHeight() != height) return result;
    std::set<juce::uint32> sampled;
    const int dx = std::max(5, width / 72);
    const int dy = std::max(5, height / 56);
    for (int y = 2; y < height; y += dy)
        for (int x = 2; x < width; x += dx) {
            const auto colour = result.image.getPixelAt(x, y).getARGB();
            sampled.insert(colour);
            result.fingerprint ^= static_cast<std::uint64_t>(colour);
            result.fingerprint *= 1099511628211ull;
        }
    result.distinctColours = static_cast<int>(sampled.size());
    return result;
}

inline Report render(juce::Component& editor, const juce::File& output,
                     const Options& options) {
    Report result;
    if (options.scenes.empty()) {
        result.errors.add("No screenshot scenes configured");
        return result;
    }
    if (output.createDirectory().failed()) {
        result.errors.add("Cannot create screenshot folder: " + output.getFullPathName());
        return result;
    }
    juce::Array<juce::var> rows;
    std::map<std::string, std::uint64_t> fingerprints;
    for (const auto& scene : options.scenes) {
        const auto id = scene.id.toStdString();
        if (scene.id.isEmpty()
            || !scene.id.containsOnly("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
            || scene.width < 64 || scene.height < 64 || scene.width > 8192 || scene.height > 8192
            || fingerprints.count(id) != 0) {
            result.errors.add("Invalid or repeated scene name/dimensions: " + scene.id);
            continue;
        }
        if (options.configure) options.configure(scene);
        auto shot = capture(editor, scene.width, scene.height);
        if (!shot.image.isValid() || shot.image.getWidth() != scene.width
            || shot.image.getHeight() != scene.height) {
            result.errors.add(scene.id + ": screenshot dimensions mismatch");
            continue;
        }
        if (shot.distinctColours < options.minimumColours) {
            result.errors.add(scene.id + ": unexpectedly blank/flat image");
            continue;
        }
        if (options.inspect)
            for (const auto& issue : options.inspect())
                result.errors.add(scene.id + ": " + issue);
        const auto file = output.getChildFile(scene.id + ".png");
        if (!writePng(shot.image, file)) {
            result.errors.add(scene.id + ": failed writing PNG");
            continue;
        }
        fingerprints[id] = shot.fingerprint;
        juce::var entry(new juce::DynamicObject());
        entry.getDynamicObject()->setProperty("file", file.getFileName());
        entry.getDynamicObject()->setProperty("width", scene.width);
        entry.getDynamicObject()->setProperty("height", scene.height);
        entry.getDynamicObject()->setProperty("theme", scene.theme);
        entry.getDynamicObject()->setProperty("mode", scene.mode);
        entry.getDynamicObject()->setProperty("browser", scene.browser);
        entry.getDynamicObject()->setProperty("sampledColours", shot.distinctColours);
        rows.add(entry);
        ++result.captured;
    }
    for (const auto& pair : options.mustDiffer) {
        const auto first = fingerprints.find(pair.first.toStdString());
        const auto second = fingerprints.find(pair.second.toStdString());
        if (first == fingerprints.end() || second == fingerprints.end()
            || first->second == second->second)
            result.errors.add("Missing or identical distinct scenes: " + pair.first + " vs " + pair.second);
    }
    juce::var manifest(new juce::DynamicObject());
    manifest.getDynamicObject()->setProperty("renderer", "SkellCore Headless JUCE Renderer v1");
    manifest.getDynamicObject()->setProperty("project", options.project);
    manifest.getDynamicObject()->setProperty("count", result.captured);
    manifest.getDynamicObject()->setProperty("scenes", juce::var(rows));
    if (!output.getChildFile("manifest.json").replaceWithText(juce::JSON::toString(manifest, false)))
        result.errors.add("Cannot save manifest.json");
    return result;
}

} // namespace skellcore::ui::headless
