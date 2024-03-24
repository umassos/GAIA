#!/bin/bash
# No Jobs Wait (Carbon and Cost Agnostic)
python3 src/run.py -r 0 --scheduling-policy carbon --carbon-policy oracle -w 0x0

# Carbon Saving per Waiting Time
python3 src/run.py -r 9 --scheduling-policy carbon --carbon-policy cst_average -w 6x24

# Spot Aware Carbon Saving per Waiting Time
python3 src/run.py -r 0 --scheduling-policy carbon-spot --carbon-policy cst_average -w 6x24

# Spot Aware - Ecovisor
python3 src/run.py -r 0 --scheduling-policy suspend-resume-spot-threshold --carbon-policy oracle -w 6x24 

# Spot - Reserved Aware (9 Reserved)
python3 src/run.py -r 9 --scheduling-policy carbon-cost-spot --carbon-policy cst_average -w 6x24

# Spot - Reserved Aware (6 Reserved)
python3 src/run.py -r 6 --scheduling-policy carbon-cost-spot --carbon-policy cst_average -w 6x24
