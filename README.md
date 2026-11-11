# SkellWorld — Connected SKELL ecosystem

SkellWorld is the **local-first connection layer** for SKELL audio software. It inventories known SKELL products, shows plugins that **explicitly join** the SW1 local hub, and displays non-privileged activity in a read-only desktop-browser console. It does **not** automatically discover or modify installed plugins.

## Run SkellWorld

**Windows (recommended):** Open [GitHub Actions](https://github.com/skellyruno/SkellWorld/actions/workflows/world-portable.yml), select a successful **SkellWorld portable Windows application** run, and download the **SkellWorld-Windows-Portable** artifact. Extract `SkellWorld-Windows-Portable.zip` inside it, then double-click `SkellWorld.exe`. Python is **not required**. The compact desktop launcher opens the web dashboard and has an **EXIT SKELLWORLD** button.

**Source/developer mode:** Double-click `Start-SkellWorld.bat` (requires Python 3) or run `python tools/skellworld_hub.py --open-browser`.

**http://127.0.0.1:48674** — read-only dashboard  
**127.0.0.1:48673** — opt-in informational plugin bus

Skell Key and SkellyTune have existing source-code WorldLink integrations; the dashboard shows live key, scale, and A4 data when a compatible Skell Key instance joins the hub. **Real two-plugin FL Studio validation is still required.** The catalog is an inventory, not an installed-plugin scanner.

See [Windows portable guide](docs/WINDOWS_PORTABLE.md) and [SkellWorld integration guide](SkellWorld/README.md).

## Separate SKELL repositories

- **SkellWorld:** local presence protocol, hub, read-only dashboard and ecosystem integration contracts.
- **SkellCore:** maintained separately at [skellcore-vst-template](https://github.com/skellyruno/skellcore-vst-template), shared DSP, JUCE UI utilities and compatible demo sources.
- **Project Hub:** separately maintained developer workspace. Future integration must use explicit consent and a permissioned API, not remote commands added to the SW1 informational protocol.
- **Individual plugin repos:** own their VST3 identities, audio code and presets. Opt-in additions must preserve host automation and saved FL Studio projects.

**Migration note:** This repository was created from the shared template, so its `SkellCore/`, `Source/` and JUCE CMake files are a **bundled compatibility snapshot**. They are not an independently updated replacement for upstream SkellCore. Keep them isolated from future hub development until a pinned dependency migration is tested.

See [SkellWorld integration guide](SkellWorld/README.md) and [protocol / architecture](docs/SKELLWORLD_ARCHITECTURE.md).

---

## Bundled SkellCore quickstart reference
Shared **Skell Audio** foundation for JUCE 8 C++17 VST3 plugins.

The former Skell VST Quickstart is preserved as a **small gain demo plugin**, with its original VST3 manufacturer, plugin code and bundle identity unchanged. Build a new plugin by choosing unique IDs; never reuse these demo IDs in commercial releases.

## Connected SKELL ecosystem

**[SkellWorld](SkellWorld/README.md)** now adds an opt-in localhost presence/events hub to the shared foundation. Run `python tools/skellworld_hub.py`, then click JOIN WORLD in two quickstart plugin instances. Other SKELL products are catalogued for gradual adoption; **they are not yet connected automatically**. No audio-thread networking or remote parameter control.

## Run SkellWorld's visual local hub

This repository also hosts the first standalone SkellWorld console. Run `python tools/skellworld_hub.py`, then visit **http://127.0.0.1:48674** (or double-click `Start-SkellWorld.bat` on Windows). The directory is an inventory, not an installed-plugin scanner. Read the [SkellWorld guide](SkellWorld/README.md).

## Contents
- `SkellCore::DSP`: portable C++17 TempoClock, PhraseTracker, OnsetDetector, four-line FDNReverb, prototype 4× interpolated-peak limiter, PitchFormantEngine.
- `SkellCore::UI`: JUCE LookAndFeel, colour themes and glow cache.
- **Production DSP backend copies**: SkellyTune RealtimeTuner v3.3 and dependencies (MIT), exact DeEsser PhraseAwareDetector behavior in a namespaced copy, and Skelly Master MasteringEngine in a namespaced copy.
- `SkellCore/backends/SkellyTuneBackend.h`: adapter matching production pitch backend to the shared `PitchFormantEngine`.
- Separate portable CI (Windows + Linux) and Windows JUCE VST3 build pipeline.

## Generate a new plugin (recommended)

```sh
python tools/new_plugin.py "Skell Compressor" ../skell-compressor-vst --code SC01
```

This creates an independent VST3 + Standalone project with an immutable SkellCore dependency, unique plugin code, generated CI, and the original quickstart gain processor. Pick a different four-character code for **every** plugin. Once you rename the GitHub template repository, use `--core-repo https://github.com/skellyruno/skellcore-vst-template.git`.

## Low-end PC performance and safety

SkellCore offers an opt-in `TruePeakLimiter::Quality::Economy` detector (2 phases × 8 taps, versus default Standard's 4 × 16), modulo-free FIR reads, bounded buffer allocations, pre-prepare bypass safety, a bounded UI glow cache, and actual Release-mode allocation/parity tests. Read [performance details](SkellCore/PERFORMANCE.md) before enabling Economy in any shipped plugin.

## v0.4 host safety and polished starter UI

The pitch/formant adapter is now lifecycle-aware: before prepare, after backend replacement, or with an incompatible channel layout, it safely passes sanitized dry audio rather than returning an undefined output. The SkellyTune DSP algorithm is unchanged; new parity tests compare it to the original at 44.1/48/96 kHz with variable host blocks and six simultaneous instances.

The starter gain effect now smooths host automation over 15 ms to reduce zipper clicks. Its UI is compact, resizable and vector-drawn with the SkellCore neon theme. The demo is built as both VST3 and Standalone for testing. **No existing demo plugin IDs or preset parameter IDs were changed.**

As always, a CI build and synthetic DSP checks do not replace real Windows FL Studio compatibility and low-end CPU validation.

## Build
```sh
cmake -S . -B build -DJUCE_PATH=/path/to/JUCE
cmake --build build --config Release
```

`JUCE_PATH` is optional; CMake otherwise fetches pinned JUCE 8.0.12.
```sh
cmake -S SkellCore -B build-core -DSKELLCORE_BUILD_TESTS=ON
cmake --build build-core --config Release
ctest --test-dir build-core -C Release --output-on-failure
```

## Reuse in other plugin repos
Copy `SkellCore/` into your monorepo, or FetchContent the **immutable commit** of this template. Example from a consumer:
```cmake
include(FetchContent)
FetchContent_Declare(SkellCore
  GIT_REPOSITORY https://github.com/skellyruno/skellcore-vst-template.git
  GIT_TAG <IMMUTABLE_COMMIT_SHA>
  SOURCE_SUBDIR SkellCore)
FetchContent_MakeAvailable(SkellCore)
target_link_libraries(MyPlugin PRIVATE SkellCore::DSP SkellCore::UI)
```
Replace `MyPlugin` with the JUCE target. The SkellCore repository has now been renamed. Use `skellyruno/skellcore-vst-template` for new builds, with an immutable, tested commit pin; the former URL only redirects for backwards compatibility.

## Integration APIs
```cpp
#include <SkellCore/Core.h>
#include <SkellCore/backends/SkellyTuneBackend.h>
skellcore::backends::SkellyTuneBackend tuning;
skellcore::PitchFormantEngine pitch;
pitch.setBackend(&tuning);
pitch.prepare(48000, 2);
auto latency = pitch.latencySamples(); // Report from prepareToPlay.
```
The production tuner exposes block processing and stable declared dry/transient latency. Do not change PDC inside processBlock and do not confuse variable pitch-cycle source age with fixed host delay.

Include `<SkellCore/backends/deesser/PhraseAwareDetector.h>` and use `skellcore::deesser::PhraseAwareDetector` for the existing DeEsser logic, and `<SkellCore/backends/master/MasteringEngine.h>` for the sampled-at-oversampled-rate mastering core. The mastering engine needs a high-quality *external* oversampler. The generic `TruePeakLimiter` is experimental; no compliance claim.

## Status and migration
This is **v0.3 shared-core work**. Source import does not automatically migrate any already released plugin. Existing DAW automation, UI layout, plugin IDs, and audio behavior must stay unchanged until validated per-plugin.

- Tuning, phrase aware, and mastering algorithms: imported, require A/B tests before plugin adoption.
- FDN reverb, prototype true peak limiter, onset tracking: functional portable modules, not production-certified.
- Host tempo / JUCE UI: available, UI not mandatory for a plugin.
- Choir: links pinned SkellCore target on separate PR; current sound unchanged.
- AdlibLab / Silence Designer / other new plugins: opt in as their CMake projects are ready.

See [SkellCore/README.md](SkellCore/README.md) and [GitHub migration tracker](https://github.com/skellyruno/skellcore-vst-template/issues/2).
