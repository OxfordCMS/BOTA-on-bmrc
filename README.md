


## License & Attribution

The MIT license in this repository applies solely to the deployment scripts, configuration files, and documentation provided here for running BOTA on the BMRC cluster at the University of Oxford.
BOTA itself is not covered by this license. [BOTA is developed by Chengwei Luo et al.](https://bitbucket.org/luo-chengwei/bota/src/master/)  and is distributed under the [BSD 3-Clause License](https://bitbucket.org/luo-chengwei/bota/src/master/License_terms.txt) . All intellectual property rights for BOTA remain with the original authors. Please refer to the original license before using, modifying, or redistributing BOTA.

## Pull the container

- We have a pre-pulled container stored in `/gpfs3/well/kir/projects/mirror/containers/bota.sif`

- If you are pull a new container image to BMRC filesystem, make sure to setup the `APPTAINER_CACHEDIR` and `APPTAINER_TMPRDIR` 
environment variables as per https://kir-rescomp.github.io/training-intro-to-apptainer/2.configuring-apptainer-cache/#setting-up-your-environment


```bash
apptainer pull bota-container.sif oras://ghcr.io/dinindusenanayake/bota-container:latest
```

## Configuration: `sample_config`

The `sample_config` file tells BOTA where to find its tool dependencies and the input data for each organism. It has two parts: a **global tool settings block** at the top, followed by one or more **named organism sections**.

### Global tool paths

The top of the file declares the paths to each external tool BOTA relies on. Inside the container these are already installed at fixed locations, so you can use bare command names for tools on `$PATH` (e.g. `hmmscan`, `prodigal`) or absolute paths for tools not on `$PATH`:

```ini
blat='/usr/local/src/blat'
hmmscan='hmmscan'
hmmtop='/usr/local/src/hmmtop_2.1/hmmtop'
psort='/usr/local/psortb/bin/psort'
prodigal='prodigal'
```

### Organism section

Each organism is declared as a named section in `[brackets]`, matching the strain or assembly name you want BOTA to use. Under it you provide three tab-separated key–value pairs:

| Key       | Description                                   |
| --------- | --------------------------------------------- |
| `fna`     | Path to the genomic FASTA (`.fna`) file       |
| `gff`     | Path to the corresponding GFF annotation file |
| `alleles` | MHC allele(s) to use for epitope prediction   |

```ini
[Citrobacter_rodentium_ATCC_51459]
fna     /gpfs3/well/kir/projects/mirror/containers/BOTA/data/Citrobacter_rodentium_ATCC_51459/GCF_000835925.1_ASM83592v1_genomic.fna
gff     /gpfs3/well/kir/projects/mirror/containers/BOTA/data/Citrobacter_rodentium_ATCC_51459/GCF_000835925.1_ASM83592v1_genomic.gff
alleles H-2-IAb
```

You can include multiple organism sections in a single config file and BOTA will process each in turn.

## Pfam Database

BOTA requires the Pfam-A HMM database for domain annotation. This is **not** included in the container and must be downloaded and prepared separately.

* We have an indexed copy of the databases stored in `/gpfs3/well/kir/projects/mirror/pfam` . If you would like to download 
your own copy and index it with the `hmmpress` in the container, below are the instructions. 

### Download

Download the latest release from the EBI Pfam FTP server:

```
ftp://ftp.ebi.ac.uk/pub/databases/Pfam/current_release
```

Fetch `Pfam-A.hmm.gz` from that directory, then decompress it:

```bash
gunzip Pfam-A.hmm.gz
```

### Prepare the HMM index

Before BOTA can use the database, you need to press it with `hmmpress` to generate the binary index files (`.h3f`, `.h3i`, `.h3m`, `.h3p`) that `hmmscan` requires. You can run this step directly via the container:

```bash
apptainer exec hbota_stepa.sif hmmpress Pfam-A.hmm
```

This will produce five files in the same directory (`Pfam-A.hmm` plus the four index files). Place all five in a single directory and point `BOTA_PFAM_DIR` at it — the `bota` wrapper will bind-mount them into the container automatically.

> **Tip:** The Pfam database is large (~3 GB compressed). Download and press it once and keep it in a shared location so it can be reused across runs.



## The `bota` wrapper script

The `bota` script is a thin Bash wrapper that takes care of all the Apptainer bookkeeping so you can call BOTA.py as if it were a regular command.

### What it does

It resolves two key paths — the Apptainer image (`.sif`) and the Pfam database directory — then launches `apptainer exec` with the correct bind-mounts before handing all arguments straight through to `BOTA.py` inside the container.

### Environment variable overrides

Rather than editing the script, you can override either default path at runtime:

| Variable        | Default                                                | Purpose                                               |
| --------------- | ------------------------------------------------------ | ----------------------------------------------------- |
| `BOTA_SIF`      | Same directory as the `bota` script                    | Path to `hbota_stepa.sif`                             |
| `BOTA_PFAM_DIR` | `/gpfs3/well/kir/projects/mirror/containers/BOTA/pfam` | Directory containing `Pfam-A.hmm` and its index files |

### Bind-mounts

The script mounts `/gpfs3/well` and `/gpfs3/users` for general GPFS access, and individually bind-mounts each of the five Pfam index files (`Pfam-A.hmm`, `.h3f`, `.h3i`, `.h3m`, `.h3p`) from your `PFAM_DIR` into the fixed location BOTA expects inside the container (`/usr/local/src/bota/BOTA/db/`). All other tools and model files are already baked into the image — no additional mounts are required.

### Sanity checks

Before launching the container, the script verifies that the `.sif` image exists and that all five Pfam files are present, giving an actionable error message if either check fails.

---

## Running BOTA

Once your config file and output directory are in place, invoke the wrapper directly:

```bash
./bota -c /gpfs3/well/kir/projects/mirror/containers/BOTA/sample_config \
       -o /gpfs3/well/kir/projects/mirror/containers/BOTA/OUTPUT \
       -t ${SLURM_CPUS_PER_TASK}
```

| Flag | Description                                                  |
| ---- | ------------------------------------------------------------ |
| `-c` | Path to your `sample_config` file                            |
| `-o` | Output directory (will be created if it doesn't exist)       |
| `-t` | Number of CPU threads — using `$SLURM_CPUS_PER_TASK` automatically picks up the allocation from your SLURM job |

> **Note:** For cluster jobs, ensure your SLURM submission requests the cores you intend to pass via `-t`, 
for example `#SBATCH --cpus-per-task=8`.



### Standard Out ( Example) 

* We can safely ignore the `W tensorflow/core/platform/cpu_feature_guard.cc:45] The TensorFlow library wasn't compiled to use SSE4.1` warnings 

```bash
➜  ./bota -c /gpfs3/well/kir/projects/mirror/containers/BOTA/sample_config -o /gpfs3/well/kir/projects/mirror/containers/BOTA/OUTPUT -t ${SLURM_CPUS_PER_TASK}                                                

Using TensorFlow backend.
################ Project Configurations ##############
[3rd party programs]
  prodigal: /usr/bin/prodigal
  hmmscan: /usr/bin/hmmscan
  hmmtop: /usr/local/src/hmmtop_2.1/hmmtop
  psort: /usr/local/psortb/bin/psort

[Citrobacter_rodentium_ATCC_51459]
  fna=/gpfs3/well/kir/projects/mirror/containers/BOTA/data/Citrobacter_rodentium_ATCC_51459/GCF_000835925.1_ASM83592v1_genomic.fna
  gff=/gpfs3/well/kir/projects/mirror/containers/BOTA/data/Citrobacter_rodentium_ATCC_51459/GCF_000835925.1_ASM83592v1_genomic.gff
  hmmtop=None
  hmmscan=None
  psort=None
        Gram=None
  [Alleles]
    H-2-IAb

################# Data Preparation ################
  [Citrobacter_rodentium_ATCC_51459] Now extracting A.A. sequences.
/usr/local/lib/python2.7/dist-packages/Bio/Seq.py:2576: BiopythonWarning: Partial codon, len(sequence) not a multiple of three. Explicitly trim the sequence or add trailing N before translation. This may become an error in future.
  BiopythonWarning)
  [Citrobacter_rodentium_ATCC_51459] Now deciding Gram stain type.
  [Citrobacter_rodentium_ATCC_51459] HMMscan against Pfam-A for domain ID.
  [Citrobacter_rodentium_ATCC_51459] Determining protein subcellular location using PSORT.
  [Citrobacter_rodentium_ATCC_51459] Now predicting transmembrane structures using HMMTOP...
  [Citrobacter_rodentium_ATCC_51459] Now PW Matrix scoring...
  [Citrobacter_rodentium_ATCC_51459] Integrating all data for DNN module...
################# DNN Model Prediction ################
2026-02-27 21:06:24.814899: W tensorflow/core/platform/cpu_feature_guard.cc:45] The TensorFlow library wasn't compiled to use SSE4.1 instructions, but these are available on your machine and could speed up CPU computations.
2026-02-27 21:06:24.814932: W tensorflow/core/platform/cpu_feature_guard.cc:45] The TensorFlow library wasn't compiled to use SSE4.2 instructions, but these are available on your machine and could speed up CPU computations.
2026-02-27 21:06:24.814938: W tensorflow/core/platform/cpu_feature_guard.cc:45] The TensorFlow library wasn't compiled to use AVX instructions, but these are available on your machine and could speed up CPU
computations.
2026-02-27 21:06:24.814943: W tensorflow/core/platform/cpu_feature_guard.cc:45] The TensorFlow library wasn't compiled to use AVX2 instructions, but these are available on your machine and could speed up CPU computations.
2026-02-27 21:06:24.814948: W tensorflow/core/platform/cpu_feature_guard.cc:45] The TensorFlow library wasn't compiled to use AVX512F instructions, but these are available on your machine and could speed up
CPU computations.
2026-02-27 21:06:24.814954: W tensorflow/core/platform/cpu_feature_guard.cc:45] The TensorFlow library wasn't compiled to use FMA instructions, but these are available on your machine and could speed up CPU
computations.
  [Citrobacter_rodentium_ATCC_51459] 176 peptides predicted.
Done.
```
