#!/bin/bash
# make_sample_list.sh
# Generates samples.txt by listing all .fna files in fna.dir,
# cross-checking that a matching .gff exists in gff.dir.
#
# Usage: bash make_sample_list.sh
# Output: samples.txt (one sample basename per line, no extension)

set -euo pipefail
cd -P "$(pwd)"

# Enter paths for files with .fna and .gff files
FNA_DIR=""
GFF_DIR=""
OUT="samples.txt"
MISSING=0

> "${OUT}"

for fna in "${FNA_DIR}"/*.fna; do
    sample=$(basename "${fna}" .fna)
    gff="${GFF_DIR}/${sample}.gff"
    if [ ! -f "${gff}" ]; then
        echo "[WARNING] No matching GFF for ${sample} -- skipping" >&2
        MISSING=$((MISSING + 1))
        continue
    fi
    echo "${sample}" >> "${OUT}"
done

TOTAL=$(wc -l < "${OUT}")
echo "Wrote ${TOTAL} samples to ${OUT}"
if [ "${MISSING}" -gt 0 ]; then
    echo "[WARNING] ${MISSING} FNA files had no matching GFF and were skipped" >&2
fi
