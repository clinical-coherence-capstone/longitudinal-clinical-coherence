#!/usr/bin/env bash
# usage: ./run_all.sh /path/to/RxNorm_full_prescribe_10052026.zip
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/build_rxnorm_component.py --zip "$1" --config-dir config --out-dir .
python3 scripts/render_docs.py --out-dir .
