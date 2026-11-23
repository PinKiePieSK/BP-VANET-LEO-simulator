"""A moved runtime must compile against its own ns-3 source tree."""
from __future__ import annotations

import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

import simulator_platform


class HeaderRelocationTest(unittest.TestCase):
    def test_native_libraries_prefer_active_runtime(self):
        with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/other/libs"}):
            value = simulator_platform.native_library_environment()["LD_LIBRARY_PATH"]
        self.assertEqual(value, f"{simulator_platform.CHECKOUT / 'build/lib'}:/other/libs")

    def test_rewrites_only_stale_generated_wrapper(self):
        with tempfile.TemporaryDirectory() as temporary:
            checkout = Path(temporary) / "vendor/ns-3.38-ocb-eval"
            source = checkout / "src/core/model/example.h"
            source.parent.mkdir(parents=True)
            source.write_text("// source\n")
            wrapper = checkout / "build/include/ns3/example.h"
            wrapper.parent.mkdir(parents=True)
            wrapper.write_text('#include "/old/runtime/vendor/ns-3.38-ocb-eval/src/core/model/example.h"\n')
            with patch.object(simulator_platform, "CHECKOUT", checkout):
                self.assertEqual(simulator_platform.repair_generated_ns3_headers(), 1)
                self.assertEqual(wrapper.read_text(), f'#include "{source}"\n')
                self.assertEqual(simulator_platform.repair_generated_ns3_headers(), 0)

    def test_does_not_hide_missing_ns3_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            checkout = Path(temporary) / "vendor/ns-3.38-ocb-eval"
            wrapper = checkout / "build/include/ns3/missing.h"
            wrapper.parent.mkdir(parents=True)
            wrapper.write_text('#include "/old/runtime/vendor/ns-3.38-ocb-eval/src/missing.h"\n')
            with patch.object(simulator_platform, "CHECKOUT", checkout):
                with self.assertRaisesRegex(RuntimeError, "Missing ns-3 source"):
                    simulator_platform.repair_generated_ns3_headers()


if __name__ == "__main__":
    unittest.main()
