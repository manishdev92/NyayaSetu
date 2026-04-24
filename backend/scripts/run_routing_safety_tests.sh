#!/usr/bin/env sh
# Fast gate: routing, authority domain, priority, emergency, crisis (NS-S1-05).
# Usage: from repo root: ./backend/scripts/run_routing_safety_tests.sh
set -e
cd "$(dirname "$0")/.."
python -m pytest \
  tests/test_crisis_triage.py \
  tests/test_hybrid_routing.py \
  tests/test_priority_engine.py \
  tests/test_emergency_detector.py \
  tests/test_emergency_intelligence.py \
  tests/test_authority_domain_resolution.py \
  tests/test_authority_hierarchy.py \
  tests/test_strict_land_guard.py \
  -q
