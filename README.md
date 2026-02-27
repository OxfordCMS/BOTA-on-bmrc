


## License & Attribution

The MIT license in this repository applies solely to the deployment scripts, configuration files, and documentation provided here for running BOTA on the BMRC cluster at the University of Oxford.
BOTA itself is not covered by this license. [BOTA is developed by Chengwei Luo et al.](https://bitbucket.org/luo-chengwei/bota/src/master/)  and is distributed under the [BSD 3-Clause License](https://bitbucket.org/luo-chengwei/bota/src/master/License_terms.txt) . All intellectual property rights for BOTA remain with the original authors. Please refer to the original license before using, modifying, or redistributing BOTA.

## How to Run the Conversion Script

```bash
apptainer exec bota.sif python2.7 convert_keras_models.py /path/to/your/models/
```
