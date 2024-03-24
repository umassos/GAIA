# Going Green for Less Green: Optimizing the Cost of Reducing Cloud Carbon Emissions

This repo presents a carbon- and cost-aware scheduling framework.

## Project Structure
```.
├── LICENSE
├── README.md
├── config-GAIA-spot.yaml # Sample Configuration for spot
├── config-GAIA.yaml #Sample Configuration for cluster
├── jobs
│   ├── nbody # Sample MPI Job
│   └── profiles # Sample Job Profile 
├── notebooks
│   ├── evaluation_plot.ipynb
├── requirements.txt
└── src
    ├── carbon.py
    ├── cluster
    ├── cluster_traces
    ├── figure10.sh
    ├── figure6-7.sh
    ├── figure8.sh
    ├── figure9.sh
    ├── run.py
    ├── scheduling
    ├── task.py
    └── traces
```

## Hardware Requirements
The code do not have any hardware requirements. The AWS tests were executed on c7gn.medium machines.

## Installation
### Simulation Environment
The simulation only requires pandas and numpy, while plotting requires seabon and matplotlib. To install requirements

```sh
pip3 install -r requirements.txt
```

### AWS ParallelCluster (Slurm) Environment
[AWS ParallelCluster](https://docs.aws.amazon.com/parallelcluster/latest/ug/install-v3-parallelcluster.html) recommends using a virtual environment.

To start a cluster for the first time follow the instructions  [here](https://docs.aws.amazon.com/parallelcluster/latest/ug/install-v3-configuring.html) and use the following command.
```
pcluster configure --config config-file.yaml
```
> Creating Our Custom Cluster
A sample of the full configuration used is in `config-GAIA.yaml` and `config-GAIA-spot.yaml`.

> An Executeble MPI Job
To create real executable MPI jobs, we built an N-body simulation MPI jobs. Setup and Execution details are available [here](jobs/nbody/README.md).

> Installing PySlurm (needed by GAIA) to communicate with AWS ParallelCluster Scheduler


```bash
export SLURM_INCLUDE_DIR=/opt/slurm/include
export SLURM_LIB_DIR=/opt/slurm/lib

git clone https://github.com/PySlurm/pyslurm.git && cd pyslurm
pip install .
```
For more details check the [official website](https://pyslurm.github.io/23.2/).

## Executing Experiment
The program takes enlisted configurations and simulates the execution of the job.

```sh
python3 src/run.py -h
usage: run.py [-h] [-c CARBON_TRACE] [--cluster-type {simulation,slurm}] [-t TASK_TRACE] [-r RESERVED_INSTANCES]
              [-w WAITING_TIMES_STR] [--scheduling-policy {carbon,carbon-spot,carbon-cost,carbon-cost-spot,cost,suspend-resume}]
              [-i START_INDEX] [--carbon-policy {waiting,lowest,oracle,cst_oracle,cst_average}] [-p CLUSTER_PARTITION]

GAIA: Carbon Aware Scheduling Policies

optional arguments:
  -h, --help            show this help message and exit
  -c CARBON_TRACE, --carbon-trace CARBON_TRACE
                        Carbon Trace
  --cluster-type {simulation,slurm}
                        Cluster Type Interface
  -t TASK_TRACE, --task-trace TASK_TRACE
                        Task Trace
  -r RESERVED_INSTANCES, --reserved-instances RESERVED_INSTANCES
                        Reserved Instances
  -w WAITING_TIMES_STR, --waiting-times WAITING_TIMES_STR
                        Waiting times per queue `x` separated
  --scheduling-policy {carbon,carbon-spot,carbon-cost,carbon-cost-spot,cost,suspend-resume}
  -i START_INDEX, --start-index START_INDEX
                        carbon start index
  --carbon-policy {waiting,lowest,oracle,cst_oracle,cst_average}
  -p CLUSTER_PARTITION, --cluster-partition CLUSTER_PARTITION
```
### Simulation Execution Examples
To reproduce Figures 8-12, we provide 4 bash scripts that customizes runs the experiments with the needed configuration. 

We provided a jupyter notebook to plot figures in `notebooks/evaluation_plot.ipynb`.

Figure 8: Normalized carbon emissions and waiting times across policies.
Figure 9: CDF of the normalized total carbon reductions.

```sh
./src/figure8-9.sh
```

Figure 10: Normalized Carbon, Cost, and Waiting Time across policies when using reserved instances.
```sh
./src/figure10.sh
```

Figure 11: Effect of reserved instances on the carbon savings and cost using a work conserving and carbon-aware scheduling policy.
```sh
./src/figure11.sh
```

Figure 12: Effect of both spot and reserved instances on the carbon savings and cost using multiple policies and configurations.
```sh
./src/figure12.sh
```

### AWS Parallel Cluster Experiments
Follow same scripts but add `--cluster-type slurm` flag to each command and execute GAIA inside the cluster master.

## Polices Mapping 
The following tables provides a mapping between policies names and acronyms used in the paper and instructions to run them i.e., the `--scheduling-policy` and `--carbon-policy` flags.

|Policy| Scheduling Policy| Carbon Policy| 
|:-:|:-:|:-:|
|No Jobs Wait (NJW)|carbon|oracle (-w 0)|
|All Jobs Wait Threshold (AJW-T)|cost|oracle|
|Lowest Carbon Slot (Lowest-Slot)|carbon|lowest|
|Lowest Carbon Widow (Lowest Window)|carbon|waiting|
|Carbon Savings per Waiting Time (Carbon-Time)|carbon|cst_average|
|Ecovisor|suspend-resume-threshold|oracle|
|Wait Awhile|suspend-resume|oracle|
|Reserved First + Carbon-Time (Res-First-Carbon-Time)| carbon-cost| cst_average|
|Spot First + Carbon-Time (Spot-First-Carbon-Time)| carbon-spot| cst_average|
|Spot First + Ecovisor (Spot-First-Ecovisor)| suspend-resume-spot-threshold| oracle|
|Spot and Reserved Aware + Carbon Time (SPOT-RES-Carbon-Time)| carbon-cost-spot | cst_average|