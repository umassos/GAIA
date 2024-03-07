# Nbody Simulation Using C++

## Installation 
```sh
sudo apt install cmake libopenmpi-dev openmpi-bin
```
## How to Build

```sh
cmake CMakeLists.txt

make
```
## RUN
```sh
./elastic_nbody [OPTIONS]

Options:
  -h,--help                   Print this help message and exit
  -b,--total-bodies INT       Total Bodies
  -r,--restore                Restore
  -p,--print                  Print initial and final values
  -c,--checkpoint-interval INT
                              Checkpoint interval
  -f,--results-folder TEXT    Results Folder
  -i,--iterations INT         Total number of iterations
```

```sh
mpirun -n 1 ./elastic_nbody -b 1000 -i 5 -c 2
```
The results include the `checkpoint.dat` and `checkpoint_time` and `iteration_time`. The current code don't include power measurements. You can use RAPL or measure utilization for this.