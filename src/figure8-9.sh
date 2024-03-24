#!/bin/bash
# Carbon Agnostic
python3 src/run.py --scheduling-policy carbon --carbon-policy oracle -w 0x0

# Lowest Carbon Slot
python3 src/run.py --scheduling-policy carbon --carbon-policy lowest -w 6x24

# Lowest Carbon Window
python3 src/run.py --scheduling-policy carbon --carbon-policy waiting -w 6x24

# Carbon Saving per Waiting Time
python3 src/run.py --scheduling-policy carbon --carbon-policy cst_average -w 6x24

# Ecovisor
python3 src/run.py --scheduling-policy suspend-resume-threshold --carbon-policy oracle -w 6x24

# Wait AWhile
python3 src/run.py --scheduling-policy suspend-resume --carbon-policy oracle -w 6x24
