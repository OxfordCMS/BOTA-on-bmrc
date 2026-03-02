#!/bin/bash -e 

#SBATCH --job-name      bota-citrobacter
#SBATCH --cpus-per-task 12
#SBATCH --mem           6G
#SBATCH --time          02:00:00
#SBATCH --output        slog/%j.out


#resolve the submission path to be absolute
cd -P ${SLURM_SUBMIT_DIR}

#make sure to use abosolute paths for config and output directory
./bota -c /gpfs3/well/kir/projects/mirror/containers/BOTA/sample_config -o /gpfs3/well/kir/projects/mirror/containers/BOTA/march02-output -t ${SLURM_CPUS_PER_TASK}
