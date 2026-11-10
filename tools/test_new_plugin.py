#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("new_plugin", ROOT / "tools" / "new_plugin.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class GeneratorTests(unittest.TestCase):
    def test_create(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "skell-compressor"
            module.make_project("Skell Compressor", dest, "SC01")
            self.assertIn("SkellCore::DSP SkellCore::UI", (dest / "CMakeLists.txt").read_text())
            self.assertIn('PLUGIN_CODE SC01', (dest / "CMakeLists.txt").read_text())
            self.assertIn('audio.skell.skellcompressor', (dest / "CMakeLists.txt").read_text())
            self.assertIn(module.DEFAULT_REV, (dest / "CMakeLists.txt").read_text())
            self.assertIn("SkellCompressorAudioProcessor", (dest / "Source" / "PluginProcessor.cpp").read_text())
            self.assertIn('skell.skellcompressor', (dest / "Source" / "PluginProcessor.h").read_text())
            self.assertIn('SkellCompressor', (dest / "Source" / "PluginProcessor.h").read_text())
            manifest=json.loads((dest / "skellworld.json").read_text())
            self.assertEqual(manifest["product_id"],"skell.skellcompressor")
            self.assertEqual(manifest["plugin_code"],"SC01")
            self.assertIn("smoothedGain_", (dest / "Source" / "PluginProcessor.h").read_text())
            self.assertIn("Skell Compressor", (dest / "Source" / "PluginEditor.cpp").read_text())
            self.assertIn("setResizable(true, true)", (dest / "Source" / "PluginEditor.cpp").read_text())
            self.assertIn("FORMATS VST3 Standalone", (dest / "CMakeLists.txt").read_text())
            self.assertTrue((dest / ".github/workflows/build.yml").exists())
            self.assertTrue((dest / ".github/workflows/ui-renderer.yml").exists())
            self.assertTrue((dest / "tools/UiRendererMain.cpp").exists())
            self.assertIn("SkellCompressorAudioProcessor", (dest / "tools/UiRendererMain.cpp").read_text())
            self.assertIn("SkellCore::UIRenderer", (dest / "CMakeLists.txt").read_text())
            self.assertIn("SkellCompressorUIRenderer", (dest / "CMakeLists.txt").read_text())
            self.assertFalse((dest / "SkellCore").exists())
            with self.assertRaises(FileExistsError):
                module.make_project("Skell Compressor", dest, "SC01")
    def test_long_product_name_gets_bounded_stable_world_id(self):
        with tempfile.TemporaryDirectory() as root:
            name = "Skell " + "Extreme" * 10
            path = Path(root) / "long"
            module.make_project(name, path, "SX11")
            product_id = json.loads((path / "skellworld.json").read_text())["product_id"]
            self.assertLess(len(product_id), 48)
            self.assertIn(product_id, (path / "Source" / "PluginProcessor.h").read_text())
    def test_invalid_identity(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "bad"
            for invalid in ["123", "abcde", "x#01", "😼😼😼😼", "Sk01", "FL26"]:
                with self.assertRaises(ValueError):
                    module.make_project("Skell Test", dest, invalid)
            self.assertFalse(dest.exists())
            with self.assertRaises(ValueError):
                module.make_project("Skell Test", dest, "ST01", core_rev="main")
            self.assertFalse(dest.exists())

if __name__ == "__main__":
    unittest.main()
