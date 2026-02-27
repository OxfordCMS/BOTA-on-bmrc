


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


