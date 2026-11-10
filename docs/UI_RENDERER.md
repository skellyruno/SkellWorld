# SkellCore headless JUCE UI renderer

The SkellCore headless renderer creates PNGs from a plugin's **actual JUCE editor** (not a mock UI or pre-rendered art). This is a C++17 header-only utility, used on the GUI/message thread. No VST3 host is needed. Linux requires a display server; use `xvfb-run` in CI.

## Reuse in any Skell plugin

Pin a commit of `skellyruno/skell-vst-template` as the SkellCore dependency (e.g. via CMake FetchContent with `SOURCE_SUBDIR SkellCore`), and link a test executable with `SkellCore::UIRenderer`. That executable must use the plugin's *real* processor and editor sources or link its existing SharedCode target.

```cpp
#include <SkellCore/HeadlessUIRenderer.h>

skellcore::ui::headless::Options options;
options.project = "My Skell Plugin";
options.scenes = {{"default", 818, 482}, {"large", 1168, 688}};
options.configure = [&](const auto& scene) {
    // Apply your real editor's theme, mode, preset-browser state, etc.
};
options.inspect = [&] { return juce::StringArray{}; }; // Your bounds assertions.
auto report = skellcore::ui::headless::render(editor, outputFolder, options);
if (!report.passed()) return 1;
```

Each scene gets a uniquely named PNG. A `manifest.json` records the dimensions, theme/mode metadata, and sampled colour count. Rendering checks image dimensions and nonblankness, plus optional layout callbacks and `mustDiffer` scene pairs. The reusable `capture()` and `writePng()` helpers can create contact sheets.

The executable must initialize JUCE first, e.g. `juce::ScopedJuceInitialiser_GUI gui;`, and keep the processor/editor alive while rendering. All editor state changes must occur on the message thread; do not call the harness from `processBlock()`.

## Template smoke build

```powershell
cmake -S . -B build -A x64 -DSKELLCORE_BUILD_UI_RENDERER=ON
cmake --build build --config Release --target SkellCoreUISmokeRenderer
# Locate and run SkellCoreUISmokeRenderer.exe with an output-directory argument.
```

Or on Linux (after installing JUCE platform headers, Xvfb and Xauth):

```bash
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DSKELLCORE_BUILD_UI_RENDERER=ON
cmake --build build --target SkellCoreUISmokeRenderer
xvfb-run -a ./build/SkellCoreUISmokeRenderer ui-screenshots
```

The template smoke tool renders the template editor at 390x250, 480x330, and 840x560. A Windows GitHub Actions workflow runs it and uploads the screenshots.

Screenshots do not certify FL Studio loading, audio output, CPU or pointer interactions. Add plugin-specific test actions and continue DSP/host tests separately.
