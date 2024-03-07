# Going Green for Less Green: Optimizing the Cost of Reducing Cloud Carbon Emissions

This repo presents a carbon- and cost-aware scheduling framework.

## Project Structure
TODO

## Hardware Requirements
The code do not have any hardware requirements. The AWS tests were executed on c7gn.medium machines.

## Installation
### Simulation Environment
The simulation only requires pandas and numpy. To install requirements

```sh
pip3 install -r requiremepip3 install -r requirements.txtnts.txt
```
### AWS ParallelCluster (Slurm) Environment
[AWS ParallelCluster](https://docs.aws.amazon.com/parallelcluster/latest/ug/install-v3-parallelcluster.html) recommends using a virtual environment.

To start a cluster for the first time follow the instructions  [here](https://docs.aws.amazon.com/parallelcluster/latest/ug/install-v3-configuring.html) and use the following command.
```
pcluster configure --config config-file.yaml
```
A sample of the full configuration used is in `config-GAIA.yaml` and `config-GAIA-spot.yaml`.

To create real executable MPI jobs, we built an N-body simulation MPI jobs. Setup and Execution details are available [here](jobs/nbody/README.md).

## Executing Experiment

