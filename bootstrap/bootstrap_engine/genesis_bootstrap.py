#!/usr/bin/env python3
"""LEGACY_NOT_FOR_EXECUTION.

The sole approval-safe executable is genesis_bootstrap_v2.py.
This wrapper only forwards explicitly to v2 so old instructions cannot invoke
an unsafe implementation.
"""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("genesis_bootstrap_v2.py")), run_name="__main__")
else:
    raise RuntimeError("LEGACY_NOT_FOR_EXECUTION: import genesis_bootstrap_v2.py instead")
