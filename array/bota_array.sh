#!/bin/bash

#SBATCH --job-name=bota_array
#SBATCH --array=1-10
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=slog/%A_%a.out
#SBATCH --error=slog/%A_%a.err

# -----------------------------------------------------------------------
# BOTA Slurm array for MAG samples
#
# Expected working directory layout:
#   bota              - wrapper script
#   BOTA.py           - patched BOTA script
#   bota.sif          - container image
#   gff_to_faa.py     - pre-generates .faa from GFF+FNA
#   samples.txt       - one sample basename per line (no extension)
#   fna.dir/          - *.fna files
#   gff.dir/          - *.gff files (same basename as .fna)
#   pfam/             - Pfam-A.hmm* files
#   configs/          - auto-generated per-sample configs (created here)
#   OUTPUT/           - BOTA output root
# -----------------------------------------------------------------------

set -euo pipefail

# Resolve symlinks to avoid Apptainer read-only bind-mount issues
cd -P "$(pwd)"

# -----------------------------------------------------------------------
# Configuration — edit these paths
# -----------------------------------------------------------------------
WORK_DIR="$(pwd)"
FNA_DIR="${WORK_DIR}/fna.dir"
GFF_DIR="${WORK_DIR}/gff.dir"
OUTPUT_DIR="${WORK_DIR}/OUTPUT"
CONFIG_DIR="${WORK_DIR}/configs"
SAMPLES_FILE="${WORK_DIR}/samples.txt"
ALLELES="H-2-IAb"   # adjust as needed

# Tool paths inside the container
HMMTOP_PATH="/usr/local/src/hmmtop_2.1/hmmtop"
PSORT_PATH="/usr/local/psortb/bin/psort"
BLAT_PATH="/usr/local/src/blat"

mkdir -p "${OUTPUT_DIR}" "${CONFIG_DIR}" slog

# -----------------------------------------------------------------------
# Get sample name for this array task
# -----------------------------------------------------------------------
SAMPLE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "${SAMPLES_FILE}")

if [ -z "${SAMPLE}" ]; then
    echo "[ERROR] No sample found for task ${SLURM_ARRAY_TASK_ID}" >&2
    exit 1
fi

FNA="${FNA_DIR}/${SAMPLE}.fna"
GFF="${GFF_DIR}/${SAMPLE}.gff"

echo "=== BOTA array task ${SLURM_ARRAY_TASK_ID}: ${SAMPLE} ==="
echo "FNA: ${FNA}"
echo "GFF: ${GFF}"

# -----------------------------------------------------------------------
# Validate inputs
# -----------------------------------------------------------------------
if [ ! -f "${FNA}" ]; then
    echo "[ERROR] FNA not found: ${FNA}" >&2
    exit 1
fi
if [ ! -f "${GFF}" ]; then
    echo "[ERROR] GFF not found: ${GFF}" >&2
    exit 1
fi

# -----------------------------------------------------------------------
# Stage 1: Pre-generate .faa from GFF + FNA
# (bypasses BOTA's internal prodigal which fails on MAG contig headers)
# -----------------------------------------------------------------------
echo "--- Stage 1: Generating .faa ---"
apptainer exec \
    --bind /gpfs3/well \
    --bind /gpfs3/users \
    bota.sif python /usr/local/src/bota/BOTA/BOTA.py --version 2>/dev/null || true

# Run gff_to_faa using the container's Python (has BioPython)
apptainer exec \
    --pwd "${WORK_DIR}" \
    --bind /gpfs3/well \
    --bind /gpfs3/users \
    --bind "${WORK_DIR}/BOTA.py:/usr/local/src/bota/BOTA/BOTA.py" \
    bota.sif python3 "${WORK_DIR}/gff_to_faa.py" \
        --fna  "${FNA}" \
        --gff  "${GFF}" \
        --genome "${SAMPLE}" \
        --outdir "${OUTPUT_DIR}"

FAA="${OUTPUT_DIR}/${SAMPLE}/${SAMPLE}.faa"
if [ ! -s "${FAA}" ]; then
    echo "[ERROR] .faa not generated or empty: ${FAA}" >&2
    exit 1
fi
echo "Generated: ${FAA}"

# -----------------------------------------------------------------------
# Stage 2: Generate per-sample BOTA config
# -----------------------------------------------------------------------
echo "--- Stage 2: Generating config ---"
CONFIG="${CONFIG_DIR}/${SAMPLE}.config"

# Use printf to ensure real tab characters between key and value
cat > "${CONFIG}" << CONFIGEOF
#BOTA config for ${SAMPLE}
blat='${BLAT_PATH}'
hmmscan='hmmscan'
hmmtop='${HMMTOP_PATH}'
psort='${PSORT_PATH}'
prodigal='prodigal'
CONFIGEOF

printf '[%s]\n' "${SAMPLE}"                          >> "${CONFIG}"
printf 'fna\t%s\n' "${FNA}"                          >> "${CONFIG}"
printf 'gff\t%s\n' "${GFF}"                          >> "${CONFIG}"
printf 'alleles\t%s\n' "${ALLELES}"                  >> "${CONFIG}"

echo "Config: ${CONFIG}"

# -----------------------------------------------------------------------
# Stage 3: Run BOTA
# -----------------------------------------------------------------------
echo "--- Stage 3: Running BOTA ---"
./bota \
    -c "${CONFIG}" \
    -o "${OUTPUT_DIR}" \
    -t "${SLURM_CPUS_PER_TASK}"

echo "=== Done: ${SAMPLE} ==="
