


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
