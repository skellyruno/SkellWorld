#!/usr/bin/env python3
"""Generate an independent JUCE VST3 project that pins, but does not copy, SkellCore."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REV = "5ac8e885f1563f804c66072797b7038bc2939fae"
DEFAULT_REPO = "https://github.com/skellyruno/skell-vst-template.git"

def make_project(name: str, destination: Path, code: str,
                 core_rev: str = DEFAULT_REV, core_repo: str = DEFAULT_REPO):
    if not re.fullmatch(r"[A-Za-z0-9]{4}", code):
        raise ValueError("--code must be exactly four ASCII letters/digits, unique to this plugin")
    # Prevent collisions with known VST3 product codes from existing SKELL
    # repositories. A collision could confuse hosts and saved projects.
    registry_path = ROOT / "SkellWorld" / "catalog.json"
    if registry_path.is_file():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for entry in registry.get("plugins", []):
            registered = entry.get("vst3_code")
            if registered and registered.lower() == code.lower():
                raise ValueError(f"Plugin code {code} is already used by {entry['repository']}")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", core_rev):
        raise ValueError("SkellCore revision must be an immutable 40-character commit SHA")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_ ]{1,79}", name):
        raise ValueError("Use 2-80 letters/digits/spaces/underscores for the plugin name")
    target = "".join(s[:1].upper() + s[1:] for s in re.findall(r"[A-Za-z0-9]+", name))
    if not target or not re.match(r"[A-Za-z]", target[0]):
        raise ValueError("Invalid project target")
    slug = re.sub(r"[^a-z0-9]+", "", name.lower())
    # The World wire identifier is max 47 characters. Keep long names
    # deterministic and collision-resistant without changing the bundle ID.
    short_slug = slug if len(slug) <= 41 else slug[:30] + hashlib.sha256(slug.encode()).hexdigest()[:10]
    world_id = f"skell.{short_slug}"
    bundle = f"audio.skell.{slug}"
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    if not (ROOT / "Source" / "PluginProcessor.cpp").is_file():
        raise FileNotFoundError("Run this generator from the SkellCore template checkout")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        src = destination / "Source"
        src.mkdir()
        for oldfile in sorted((ROOT / "Source").iterdir()):
            if oldfile.suffix not in (".cpp", ".h"):
                continue
            body = oldfile.read_text(encoding="utf-8")
            body = body.replace("SkellAudioProcessor", f"{target}AudioProcessor")
            body = body.replace("Skell Quickstart", name)
            body = body.replace("skellcore.quickstart", world_id)
            (src / oldfile.name).write_text(body, encoding="utf-8")
        cmake = f'''cmake_minimum_required(VERSION 3.22)
project({target} VERSION 1.0.0 LANGUAGES C CXX)
include(FetchContent)
if(DEFINED JUCE_PATH AND EXISTS "${{JUCE_PATH}}/CMakeLists.txt")
  add_subdirectory("${{JUCE_PATH}}" JUCE)
else()
  FetchContent_Declare(JUCE GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
      GIT_TAG 8.0.12 GIT_SHALLOW TRUE)
  FetchContent_MakeAvailable(JUCE)
endif()
FetchContent_Declare(SkellCore
    GIT_REPOSITORY {core_repo}
    GIT_TAG {core_rev}
    SOURCE_SUBDIR SkellCore)
FetchContent_MakeAvailable(SkellCore)
juce_add_plugin({target}
    COMPANY_NAME "Skell Audio"
    BUNDLE_ID "{bundle}"
    PLUGIN_MANUFACTURER_CODE SkAu
    PLUGIN_CODE {code}
    FORMATS VST3 Standalone
    PRODUCT_NAME "{name}"
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT FALSE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    COPY_PLUGIN_AFTER_BUILD FALSE)
juce_generate_juce_header({target})
target_sources({target} PRIVATE Source/PluginProcessor.cpp Source/PluginProcessor.h
    Source/PluginEditor.cpp Source/PluginEditor.h)
target_compile_features({target} PRIVATE cxx_std_17)
target_compile_definitions({target} PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_VST3_CAN_REPLACE_VST2=0)
target_link_libraries({target} PRIVATE SkellCore::DSP SkellCore::UI
    juce::juce_audio_utils juce::juce_audio_processors juce::juce_gui_extra)
'''
        # Screenshot harness is opt-in: real generated editor, no VST3 host.
        cmake += f"""
option(SKELLCORE_BUILD_UI_RENDERER "Build real JUCE editor screenshots" OFF)
if(SKELLCORE_BUILD_UI_RENDERER)
  add_executable({target}UIRenderer tools/UiRendererMain.cpp)
  target_include_directories({target}UIRenderer PRIVATE
      "${{CMAKE_CURRENT_BINARY_DIR}}/{target}_artefacts/JuceLibraryCode")
  target_link_libraries({target}UIRenderer PRIVATE {target} SkellCore::UIRenderer
      SkellCore::DSP juce::juce_audio_utils juce::juce_gui_extra)
  target_compile_definitions({target}UIRenderer PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)
  target_compile_features({target}UIRenderer PRIVATE cxx_std_17)
endif()
"""
        ui_tools = destination / "tools"
        ui_tools.mkdir()
        renderer_source = (ROOT / "tools" / "SkellCoreUiRendererMain.cpp").read_text(encoding="utf-8")
        renderer_source = renderer_source.replace("SkellAudioProcessor", f"{target}AudioProcessor")
        renderer_source = renderer_source.replace("SkellCore template quickstart", name)
        renderer_source = renderer_source.replace("quickstart_", "plugin_")
        (ui_tools / "UiRendererMain.cpp").write_text(renderer_source, encoding="utf-8")
        (destination / "CMakeLists.txt").write_text(cmake, encoding="utf-8")
        workflow = '''name: Build Windows VST3
on:
  workflow_dispatch:
  push:
    branches: [main]
  pull_request:
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure
        run: cmake -S . -B build -A x64
      - name: Build
        run: cmake --build build --config Release --parallel 2
      - name: Package
        shell: pwsh
        run: |
          $plugin = Get-ChildItem -Path build -Directory -Recurse -Filter '*.vst3' | Select-Object -First 1
          if (-not $plugin) { throw 'VST3 bundle missing' }
          Compress-Archive -Path $plugin.FullName -DestinationPath Skell-Plugin-VST3.zip
      - uses: actions/upload-artifact@v4
        with:
          name: Skell-Plugin-VST3
          path: Skell-Plugin-VST3.zip
          if-no-files-found: error
'''
        wf = destination / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "build.yml").write_text(workflow, encoding="utf-8")
        ui_workflow = """name: Headless JUCE UI screenshots
on:
  push:
    branches: [main]
    paths: ['CMakeLists.txt', 'Source/**', 'tools/UiRendererMain.cpp', '.github/workflows/ui-renderer.yml']
  pull_request:
  workflow_dispatch:
jobs:
  render:
    runs-on: windows-latest
    timeout-minutes: 40
    steps:
      - uses: actions/checkout@v4
      - name: Configure actual-editor renderer
        run: cmake -S . -B build -A x64 -DSKELLCORE_BUILD_UI_RENDERER=ON
      - name: Build actual-editor renderer
        run: cmake --build build --config Release --target __RENDERER__ --parallel 2
      - name: Capture real JUCE editor
        shell: pwsh
        run: |
          $exe = Get-ChildItem build -Recurse -File -Filter __RENDERER__.exe | Select-Object -First 1
          if (-not $exe) { throw 'Renderer executable missing' }
          & $exe.FullName (Join-Path (Get-Location) 'ui-screenshots')
          if ($LASTEXITCODE -ne 0) { throw "Renderer failed: $LASTEXITCODE" }
          if (@(Get-ChildItem ui-screenshots -Filter *.png).Count -ne 3) { throw 'Expected three screenshot PNGs' }
      - uses: actions/upload-artifact@v4
        with:
          name: Skell-UI-Screenshots
          path: ui-screenshots/*
          if-no-files-found: error
"""
        ui_workflow = ui_workflow.replace("__RENDERER__", f"{target}UIRenderer")
        (wf / "ui-renderer.yml").write_text(ui_workflow, encoding="utf-8")

        text = f"""# {name}
Generated from SkellCore VST Template. The original demo processing is a gain knob.

- Product: {name}
- Bundle ID: {bundle}
- Manufacturer code: SkAu
- Unique VST3 plugin code: {code}
- Shared SkellCore source: {core_repo}@{core_rev}

## Build
```sh
cmake -S . -B build -DJUCE_PATH=/path/to/JUCE
cmake --build build --config Release
```

SkellCore is fetched by a pinned commit. Only update that pin after testing.\n\nThe generated project includes an opt-in **real JUCE UI screenshot renderer**:\n\n```sh\ncmake -S . -B build -DSKELLCORE_BUILD_UI_RENDERER=ON\ncmake --build build --config Release --target {target}UIRenderer\n```\n\nRun `{target}UIRenderer` with an output folder argument, or use the GitHub Actions **Headless JUCE UI screenshots** workflow. Configure additional themes and layouts in `tools/UiRendererMain.cpp`.
To build in GitHub, upload this generated folder as its own repository and run Actions.
Do not reuse the same plugin code or bundle ID in two shipping plugins.
"""
        (destination / "README.md").write_text(text, encoding="utf-8")
        # A stable, machine-readable identity for future SkellWorld cataloguing.
        world_manifest = {
            "schema": "skellworld-plugin/1",
            "product_id": world_id,
            "name": name,
            "manufacturer": "Skell Audio",
            "plugin_code": code,
            "bundle_id": bundle,
            "connection": "explicit-opt-in-loopback",
            "capabilities": ["presence", "informational-events"],
        }
        (destination / "skellworld.json").write_text(
            json.dumps(world_manifest, indent=2) + "\n", encoding="utf-8")
        (destination / ".gitignore").write_text("/build/\n.vs/\n*.user\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(destination)
        raise
    return destination

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("name", help='Product name, e.g. "Skell Compressor"')
    p.add_argument("destination", type=Path, help="New folder (must not already exist)")
    p.add_argument("--code", required=True, help="Four-character unique VST3 plugin code")
    p.add_argument("--core-rev", default=DEFAULT_REV)
    p.add_argument("--core-repo", default=DEFAULT_REPO)
    a = p.parse_args()
    try:
        print(f"Created {make_project(a.name, a.destination, a.code, a.core_rev, a.core_repo)}")
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        p.error(str(exc))

if __name__ == "__main__":
    main()
