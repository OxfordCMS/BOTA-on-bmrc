# BOTA — Slurm Array for MAG Analysis

This directory contains scripts for running BOTA at scale on MAGs (Metagenome-Assembled Genomes) via a Slurm job array. It is a companion to the main BOTA setup — refer to the root README for container setup, Pfam database preparation, and single-sample usage.

---

## Contents

| File | Description |
|------|-------------|
| `BOTA.py` | Patched BOTA script (see [Patches](#bota-patches) below) |
| `gff_to_faa.py` | Pre-generates `.faa` from GFF+FNA for MAG input |
| `make_sample_list.sh` | Generates `samples.txt` from `fna.dir/` and `gff.dir/` |
| `bota_array.sh` | Slurm array submission script |

---

## Why a separate workflow for MAGs?

BOTA's internal gene calling (Prodigal) fails on MAG contigs due to non-standard sequence headers produced by assemblers like MetaBat2 or CONCOCT. Rather than fighting BOTA's internals, we pre-generate the `.faa` protein file from your existing GFF annotation using `gff_to_faa.py`. BOTA detects the pre-generated `.faa` and skips its internal gene calling step entirely.

---

## Input Structure

```
workdir/
├── bota                  # wrapper script (from repo root)
├── BOTA.py               # patched BOTA script (this directory)
├── bota.sif              # Apptainer container image
├── fna.dir/              # one .fna per sample
│   ├── sample1.fna
│   └── sample2.fna
├── gff.dir/              # matching .gff per sample (same basename)
│   ├── sample1.gff
│   └── sample2.gff
└── pfam/                 # Pfam-A.hmm* files (or use BMRC shared path)
```

>**Important**- FNA and GFF filenames must share the same basename — `sample1.fna` pairs with `sample1.gff`.

---

## Usage

**Step 1:** Generate the sample list:

- Update `FNA_DIR` and `GFF_DIR` varibales in `make_sample_list.sh` to reflect the paths to .fna and .gff files, respectively. 

```bash
bash make_sample_list.sh
wc -l samples.txt    # verify count
```

This cross-checks every `.fna` in `fna.dir/` against `gff.dir/` and warns about any missing GFF files.

**Step 2:** Update the `--array` line in `bota_array.sh` to match your sample count:

- In this instance, we have 1333 samples. Hence the array index is `1-1333`. We are throttling the number of concurrent jobs to 300 with `%300`

```bash
#SBATCH --array=1-1333%300    # adjust 1333 to your total, %300 = max concurrent
```

**Step 3** Refer to `Configuration — edit these paths` in `bota_array.sh` script. Make sure the paths to .fna and .gff files are correct. 

```bash
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
```

**Step 4:** Submit:
```bash
sbatch bota_array.sh
```

Each array task runs three stages automatically:
1. Pre-generates `.faa` and `.ffn` from GFF+FNA via `gff_to_faa.py`
2. Writes a per-sample config to `configs/`
3. Runs BOTA via the `bota` wrapper

Logs are written to `slog/JOBID_TASKID.{out,err}`.

**Monitor progress:**
```bash
sacct -j JOBID -n -o jobid%30,state%20 | grep -v '\.' | sort -t_ -k2 -n
```

**Check failures:**
```bash
sacct -j JOBID -n -o jobid%30,state%20 \
    | awk '!/\./ && /FAILED|TIMEOUT|OUT_OF_MEMORY/ {
        split($1,a,"_"); if(a[2]!="") ids=ids (ids?",":"") a[2]
      } END{print ids}'
```

---

## BOTA Patches

The `BOTA.py` in this directory includes four fixes over the original required for MAG compatibility:

| Line | Error | Fix |
|------|-------|-----|
| 84 | `ImportError: No module named keras.models` | Keras import was commented out in original — uncommented |
| 466 | `OSError: *.hmmscan.temp not found` | Added `os.path.exists()` guard before `os.unlink()` |
| 868 | `OSError: hmmtop.arch not found` | Added `os.path.exists()` guard before `os.unlink()` |
| 109 | `AttributeError: GeneInfo has no attribute 'hmmtop'` | Initialised `self.hmmtop = []` in `GeneInfo.__init__` — handles MAGs with zero TM predictions |

> If you need to re-apply these patches to a fresh `BOTA.py`, refer to the patch commands in issues

---

## Output

Results are written to `OUTPUT/SAMPLE_NAME/`:

| File | Description |
|------|-------------|
| `SAMPLE.faa` | Protein sequences (pre-generated from GFF) |
| `SAMPLE.hmmscan` | Pfam domain hits |
| `SAMPLE.hmmtop` | Transmembrane topology (empty = no TM helices predicted) |
| `SAMPLE.psort` | Subcellular localisation predictions |
| `SAMPLE.pwm` | Position weight matrix scores |
| `SAMPLE_ALLELE.bota.txt` | Final BOTA antigen predictions |
