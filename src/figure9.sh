#!/bin/bash
# Reserved First -  Carbon Saving per Waiting Time

# Reserved = 0 - 24
for r in 0 3 6 9 12 15 18 21 24
do
    python3 src/run.py -r "$r" --scheduling-policy carbon-cost --carbon-policy cst_average -w 6x24
done

