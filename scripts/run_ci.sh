#!/usr/bin/env bash
set -euo pipefail
# Layer 1: contract checks only. Zero network, under a minute.
python -m pytest -m contract -q
