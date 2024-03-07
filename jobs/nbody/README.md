# Nbody Simulation Using C++

## Installation 
```
sudo apt install cmake libopenmpi-dev openmpi-bin
```
## How to Build

```
cmake CMakeLists.txt

make
```
## RUN
```
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

```
mpirun -n 1 ./elastic_nbody -b 1000 -i 5 -c 2
```
Different machines may requires different configurations, you might need `--allow-run-as-root` if you're running inside a container.

The results include the `checkpoint.dat` and `checkpoint_time` and `iteration_time`. The current code don't include power measurements. You can use RAPL or measure utilization for this.

## Running in Docker
This is the easiest way to run the workload. This can run on any machine.
```
sudo docker build -t washraf/nbody .
# sudo docker push washraf/nbody # If you need it available globally
docker run -it washraf/nbody
# mpirun --allow-run-as-root -n 1 ./elastic_nbody -b 1000 -i 5 -c 1
```