#!/usr/bin/env python3
import argparse
from typing import List
import pandas as pd
from carbon import get_carbon_model, CarbonModel
from task import Task, set_waiting_times, load_tasks, TIME_FACTOR
from scheduling import create_scheduler
from cluster import create_cluster
import hashlib
import time

def run_experiment(cluster_type: str, carbon_start_index: int, carbon_model: CarbonModel, tasks: List[Task], scheduling_policy: str, carbon_policy: str, reserved_instances: int, task_trace:str, waiting_times_str:str, cluster_partition:str):
    """Run Experiments

    Args:
        cluster_type (str): cluster Type
        carbon_start_index (int): carbon trace start time
        scheduling_policy (str): scheduling algorithm
        carbon_policy (str): carbon waiting policy
        reserved_instances (int): number of reserved instances
        waiting_times_str (str): waiting times per queue
        task_trace (str): Task Trace
        waiting_times_str (str): waiting times per queue
        cluster_partition (str): used cluster partition (queue), only for slurm experiment.

    Returns:
        List: Results
    """
    experiment_name = hashlib.md5(
        f"{carbon_model.name}-{carbon_start_index}-{scheduling_policy}-{carbon_policy}-{waiting_times_str}-{reserved_instances}-{task_trace}-{cluster_partition}".encode()).hexdigest()[:10]
    cluster = create_cluster(cluster_type, scheduling_policy, carbon_model, reserved_instances,
                             experiment_name, waiting_times_str, cluster_partition)
    scheduler = create_scheduler(cluster, scheduling_policy, carbon_policy,
                                 carbon_model)
    for i in range(0, carbon_model.df.shape[0]):
        current_time = i
        if cluster_type == "slurm":
            current_time = max(i, round(time.time() - cluster.experiment_start))
            #if current_time != i:
            #    print(f"Current time = {current_time} with i = {i}")
        while len(tasks) > 0:
            if tasks[0].arrival_time <= current_time:
                if tasks[0].task_length > 0:
                    scheduler.submit(current_time, tasks[0])
                del tasks[0]
            else:
                break
        with cluster.lock:
            scheduler.execute(current_time)
        cluster.sleep()
        if len(tasks) == 0 and scheduler.queue.empty() and cluster.done():
            break
    cluster.save_results(cluster_type, scheduling_policy, carbon_policy,
                         carbon_model.name, task_trace, waiting_times_str)
    return [cluster.total_carbon_cost, cluster.total_dollar_cost]


def prepare_experiment(cluster_type: str, carbon_start_index: int, carbon_trace: str, task_trace: str, scheduling_policy: str, carbon_policy: str, reserved_instances: int, waiting_times_str: str, cluster_partition: str):
    """Prepare and Run Experiment 

    Args:
        cluster_type (str): cluster Type
        carbon_start_index (int): carbon trace start time
        carbon_trace (str): carbon trace name
        task_trace (str): task trace name
        scheduling_policy (str): scheduling algorithm
        carbon_policy (str): carbon waiting policy
        reserved_instances (int): number of reserved instances
        waiting_times_str (str): waiting times per queue
        cluster_partition (str): used cluster partition (queue), only for slurm experiment.
    """
    print(
        f"Start Experiments {task_trace} - {carbon_trace}-{scheduling_policy}-{carbon_policy}-{waiting_times_str}, and {reserved_instances} reserved")
    set_waiting_times(waiting_times_str)
    carbon_model = get_carbon_model(carbon_trace, carbon_start_index)
    tasks = load_tasks(task_trace)
    carbon_model = carbon_model.extend(3600 / TIME_FACTOR)
    results = []
    result = run_experiment(cluster_type, carbon_start_index, carbon_model, tasks, scheduling_policy,
                            carbon_policy, reserved_instances, task_trace, waiting_times_str, cluster_partition)
    results.append(result)
    results = pd.DataFrame(results, columns=[
                           "carbon_cost", "dollar_cost"])
    file_name = f"results/{cluster_type}/{task_trace}/{scheduling_policy}-{carbon_start_index}-{carbon_policy}-{carbon_trace}-{reserved_instances}-{waiting_times_str}.csv"
    results.to_csv(file_name, index=False)
    print(
        f"Finish Experiments {task_trace} - {carbon_trace}-{scheduling_policy}-{carbon_policy}-{waiting_times_str}, and {reserved_instances} reserved")


def main():
    parser = argparse.ArgumentParser(
        description='Single Task Carbon Scheduling Simulation')
    parser.add_argument("-c", "--carbon-trace", default="AU-SA",  # "CA-ON",# "US-CAL-CISO", "SE-SE1"
                        type=str, dest="carbon_trace", help="Carbon Trace")
    parser.add_argument("--cluster-type", default="simulation", type=str, choices=["simulation", "slurm"],
                        dest="cluster_type", help="Cluster Type Interface")
    parser.add_argument("-t", "--task-trace", default="pai_new_trace",
                        type=str,
                        dest="task_trace",
                        help="Task Trace")
    parser.add_argument("-r", "--reserved-instances", type=int,
                        default=9, dest="reserved_instances", help="Reserved Instances")
    parser.add_argument("-w", "--waiting-times", type=str,
                        default="1000x1000", dest="waiting_times_str", help="Waiting times per queue x separated")
    parser.add_argument("--scheduling-policy",
                        default="cost", dest="scheduling_policy")
    parser.add_argument("-i", "--start-index", type=int, default=7000,
                        dest="start_index", help="carbon start index")
    parser.add_argument("--carbon-policy", default="oracle",
                        dest="carbon_policy", choices=["waiting", "lowest", "oracle", "cst_oracle", "cst_average"])
    parser.add_argument("-p", "--cluster-partition",
                        default="queue1", dest="cluster_partition")

    args = parser.parse_args()
    carbon_start_index = []
    if args.start_index == -1:
        carbon_starts = range(0, 8500, 500)
    else:
        carbon_starts = [args.start_index]
    for carbon_start_index in carbon_starts:
        prepare_experiment(args.cluster_type, carbon_start_index, args.carbon_trace, args.task_trace, args.scheduling_policy,
                           args.carbon_policy, args.reserved_instances, args.waiting_times_str, args.cluster_partition)


if __name__ == "__main__":
    main()
