#!/usr/bin/env bash
# Reproduce the cross-modal refusal-direction experiment.
#
# Extraction and analysis run on the Jetson AGX Orin (CPU, float32) in a Python 3.11 env
# with transformers >= 4.49. Rendering and the dashboard run anywhere with Pillow/Streamlit.
#
#   ./run_experiment.sh render            # data/images/*.png + data/items.json (any machine)
#   ./run_experiment.sh smoke  MODEL      # 2 pairs end to end, prints timings
#   ./run_experiment.sh run    MODEL      # all 100 pairs, resumable
#   ./run_experiment.sh analyze MODEL     # metrics, held-out scores, figures 1-4
#   ./run_experiment.sh compare           # figure 5 across models
#   ./run_experiment.sh dashboard         # streamlit app
#
# MODEL is a Hugging Face id, e.g. Qwen/Qwen2.5-VL-3B-Instruct or Qwen/Qwen2.5-VL-7B-Instruct.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-python3}
case "${1:-}" in
  render)    (cd src && $PY render.py) ;;
  smoke)     $PY src/extract.py --model "$2" --pairs 2 ;;
  run)       $PY src/extract.py --model "$2" ;;
  analyze)   $PY src/analyze.py --model "${2##*/}" ;;
  compare)   $PY src/compare.py ;;
  dashboard) streamlit run src/dashboard.py ;;
  *) sed -n '2,15p' "$0"; exit 1 ;;
esac
