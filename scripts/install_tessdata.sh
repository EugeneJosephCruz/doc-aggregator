#!/usr/bin/env bash
# Download additional tessdata language packs into the active conda env.
# Usage: conda activate doc-aggregator && bash scripts/install_tessdata.sh

set -euo pipefail

TESSDATA_DIR="${CONDA_PREFIX}/share/tessdata"
BASE_URL="https://github.com/tesseract-ocr/tessdata_fast/raw/main"

LANGUAGES=("spa")

mkdir -p "$TESSDATA_DIR"

for lang in "${LANGUAGES[@]}"; do
    dest="${TESSDATA_DIR}/${lang}.traineddata"
    if [ -f "$dest" ]; then
        echo "Already installed: ${lang}.traineddata"
    else
        echo "Downloading ${lang}.traineddata ..."
        curl -fsSL -o "$dest" "${BASE_URL}/${lang}.traineddata"
        echo "Installed: ${dest}"
    fi
done

echo ""
echo "Installed tessdata packs:"
ls "$TESSDATA_DIR"/*.traineddata 2>/dev/null | xargs -n1 basename
