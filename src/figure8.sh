#!/bin/bash
# No Jobs Wait (Carbon and Cost Agnostic)
python3 src/run.py -r 9 --scheduling-policy carbon --carbon-policy oracle -w 0x0

# All Jobs Wait
python3 src/run.py -r 9 --scheduling-policy cost --carbon-policy oracle -w 6x24

# Wait AWhile
python3 src/run.py -r 9 --scheduling-policy suspend-resume --carbon-policy oracle -w 6x24

# Lowest Carbon Window
python3 src/run.py -r 9 --scheduling-policy carbon --carbon-policy waiting -w 6x24

# Carbon Saving per Waiting Time
python3 src/run.py -r 9 --scheduling-policy carbon --carbon-policy cst_average -w 6x24

# Reserved First -  Lowest Carbon Window
python3 src/run.py -r 9 --scheduling-policy carbon-cost --carbon-policy waiting -w 6x24

# Reserved First -  Carbon Saving per Waiting Time Carbon Window
python3 src/run.py -r 9 --scheduling-policy carbon-cost --carbon-policy cst_average -w 6x24
