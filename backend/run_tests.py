#!/usr/bin/env python3
"""
Run backend unit tests from anywhere:

  python run_tests.py              # cwd = backend/
  python backend/run_tests.py      # cwd = repo root (NyayaSetu/)

Uses unittest discover with top_level_dir=backend so `from app...` imports work.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TESTS_DIR = BACKEND_ROOT / "tests"


def main() -> int:
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(TESTS_DIR),
        pattern="test_*.py",
        top_level_dir=str(BACKEND_ROOT),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
