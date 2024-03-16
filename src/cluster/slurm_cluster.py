from collections.abc import Callable, Iterable, Mapping
import sys
from threading import Thread
from typing import Any, List
from carbon import CarbonModel
from .base_cluster import BaseCluster
from task import Task
import pandas as pd
import os
import time
import pyslurm
from scheduling.carbon_waiting_policy import compute_carbon_consumption
from collections import namedtuple
from datetime import datetime

TResult = namedtuple(
    "TResult",
    "jobname submit start end elapsed req_cpus state_str exitcode nodes partition",
)

NResult = namedtuple("NResult", "node_name cpus coes partitions state")
KNOWN_STATES = [
    "IDLE+CLOUD",
    "IDLE!+CLOUD",
    "IDLE#+CLOUD",
    "IDLE+CLOUD+POWER",
    "IDLE+CLOUD+POWERING_DOWN",
    "IDLE+CLOUD+COMPLETING",
    "ALLOCATED+CLOUD",
    "ALLOCATED#+CLOUD",
    "ALLOCATED+CLOUD+POWER",
]


def get_final_tasks(cluster_partition, start_ts) -> List[TResult]:
    tresults = []
    try:
        start_time = datetime.utcfromtimestamp(start_ts).strftime("%Y-%m-%dT00:00:00")
        jobs = pyslurm.slurmdb_jobs()
        jobs_dict = jobs.get(
            starttime=start_time.encode("utf-8"),
        )
        if jobs_dict:
            for job_id, job_detail in jobs_dict.items():
                tresult = TResult(
                    jobname=job_detail["jobname"],
                    submit=round(job_detail["submit"] - start_ts),
                    start=round(job_detail["start"] - start_ts),
                    end=round(job_detail["end"] - start_ts),
                    elapsed=job_detail["elapsed"],
                    req_cpus=job_detail["req_cpus"],
                    state_str=job_detail["state_str"],
                    exitcode=job_detail["exitcode"],
                    nodes=job_detail["nodes"],
                    partition=job_detail["partition"],
                )
                if cluster_partition not in job_detail["partition"]:
                    continue
                if tresult.submit < -1:
                    continue
                # assert tresult.state_str == "COMPLETED" or tresult.state_str == "TIMEOUT"
                tresults.append(tresult)
            return tresults
        else:
            return None
    except Exception as execption:
        print(f"Error:{execption.args[0]}")
        return None


class SlurmCluster(BaseCluster):
    def __init__(
        self,
        reserved_instances: int,
        carbon_model: CarbonModel,
        experiment_name: str,
        cluster_partition: str,
        allow_spot,
    ) -> None:
        super().__init__(
            reserved_instances=reserved_instances,
            carbon_model=carbon_model,
            experiment_name=experiment_name,
            allow_spot=allow_spot,
        )
        self.experiment_start = time.time()
        self.last_sleep = time.time()
        self.cluster_partition = cluster_partition
        self.task_dict = {}
        self.running_jobs = -1
        self.slurmMonitor: SlurmMonitor = SlurmMonitor(self)
        self.slurmMonitor.start()

    def submit(self, current_time, task: Task):
        try:
            df = pd.read_csv("jobs/profiles/nbody100k.csv")
            iter_time = df[df["nodes"] == task.CPUs]["iteration_time"].mean()
            iters = round(task.task_length / iter_time)
            minutes = round(iters * iter_time / 60)
            print(f"Expected time is:{minutes} minutes")
            c_model = self.carbon_model.subtrace(
                current_time,
                current_time + max(task.task_length, task.expected_time) + 1,
            )
            schedule = compute_carbon_consumption(task, 0, c_model)
            if self.allow_spot and task.task_length_class == "0-2":
                partitions = [self.cluster_partition + "spot"]
                reserved = 0
                task.reserved = reserved
                self.log_task(
                    current_time,
                    task,
                    task.CPUs * task.task_length * self.spot_cost,
                    schedule.carbon_cost,
                )
            else:
                partitions = [self.cluster_partition]
                if self.available_reserved_instances >= task.CPUs:
                    on_demand = 0
                    reserved = task.CPUs
                elif (
                    self.available_reserved_instances < task.CPUs
                    and self.available_reserved_instances > 0
                ):
                    on_demand = task.CPUs - self.available_reserved_instances
                    reserved = self.available_reserved_instances
                else:
                    on_demand = task.CPUs
                    reserved = 0
                task.reserved = reserved
                self.available_reserved_instances -= reserved
                self.log_task(
                    current_time,
                    task,
                    on_demand * task.task_length * self.on_demand_cost,
                    schedule.carbon_cost,
                )

            name = f"{task.ID}-{self.experiment_name}"
            self.task_dict[name] = task
            print(f"Submiting {name} for {task.CPUs} CPUs and {reserved} reserved")
            desc = pyslurm.JobSubmitDescription(
                name=name,
                nodes=task.CPUs,
                ntasks=task.CPUs,
                script="/home/ubuntu/ParallelCluster/src/cluster_traces/nbody.sh",
                script_args=f"100000 {iters} results-{name}/",
                partitions=partitions,
                time_limit=minutes,
            )
            job_id = desc.submit()

        except ValueError as value_error:
            print(f"Job query failed - {value_error.args[0]}")
            sys.exit(1)

    def refresh_data(self, current_time):
        return

    def collect_slurm_results(
        self,
        cluster_type: str,
        scheduling_policy,
        carbon_policy,
        carbon_trace,
        task_trace,
        waiting_times_str,
    ):
        self.slurmMonitor.started = False
        tresults = get_final_tasks(self.cluster_partition, self.experiment_start)
        real_details = []
        for tresult in tresults:
            task = self.task_dict[tresult.jobname]
            waiting_time = max(tresult.submit - task.arrival_time, 0)
            self.max_time = max(self.max_time, tresult.start)

            execution_carbon = self.carbon_model.df["carbon_intensity_avg"][
                tresult.start : tresult.end
            ]
            run_carbon = (
                execution_carbon.sum() * tresult.req_cpus
            )  # 1 watt per core for now
            execution_carbon = self.carbon_model.df["carbon_intensity_avg"][
                tresult.submit : tresult.end
            ]
            total_carbon = (
                execution_carbon.sum() * tresult.req_cpus
            )  # 1 watt per core for now

            if "spot" in tresult.partition:
                assert task.reserved == 0
                run_dollar_cost = tresult.elapsed * self.spot_cost * tresult.req_cpus
                total_dollar_cost = (
                    (tresult.end - tresult.submit) * self.spot_cost * tresult.req_cpus
                )
            else:
                run_dollar_cost = (
                    tresult.elapsed
                    * self.on_demand_cost
                    * (tresult.req_cpus - task.reserved)
                )
                total_dollar_cost = (
                    (tresult.end - tresult.submit)
                    * self.on_demand_cost
                    * (tresult.req_cpus - task.reserved)
                )

            real_details.append(
                [
                    tresult.jobname,
                    task.arrival_time,
                    task.task_length,
                    tresult.req_cpus,
                    task.task_length_class,
                    task.CPUs_class,
                    run_carbon,
                    total_carbon,
                    run_dollar_cost,
                    total_dollar_cost,
                    tresult.submit,
                    tresult.start,
                    waiting_time,
                    tresult.end,
                    tresult.state_str,
                ]
            )
        reserved_cost = (
            self.total_reserved_instances
            * self.reserved_discount_rate
            * self.max_time
            * self.on_demand_cost
        )
        real_details.append(
            [-1, 0, 0, 0, 0, 0, 0, 0, reserved_cost, reserved_cost, 0, 0, 0, 0, 0]
        )
        df = pd.DataFrame(
            real_details,
            columns=[
                "ID",
                "arrival_time",
                "length",
                "cpus",
                "length_class",
                "resource_class",
                "carbon_cost",
                "total_carbon_cost",
                "dollar_cost",
                "total_dollar_cost",
                "submit_time",
                "start_time",
                "waiting_time",
                "exit_time",
                "reason",
            ],
        )

        os.makedirs(f"results/{cluster_type}/{task_trace}/", exist_ok=True)
        file_name = f"results/{cluster_type}/{task_trace}/slurm-details-{scheduling_policy}-{self.carbon_model.carbon_start_index}-{carbon_policy}-{carbon_trace}-{self.total_reserved_instances}-{waiting_times_str}.csv"
        df.to_csv(file_name, index=False)
        self.total_carbon_cost = self.slurmMonitor.total_carbon_cost
        self.total_dollar_cost = self.slurmMonitor.total_dollar_cost
        self.total_dollar_cost += (
            self.total_reserved_instances
            * self.reserved_discount_rate
            * self.max_time
            * self.on_demand_cost
        )
        df = pd.DataFrame(
            self.slurmMonitor.details,
            columns=[
                "time",
                "power_on",
                "power_on_spot",
                "power_on_total",
                "reserved_idle",
                "running_jobs",
            ],
        )
        file_name = f"results/slurm/{task_trace}/slurm-runtime-{scheduling_policy}-{self.carbon_model.carbon_start_index}-{carbon_policy}-{carbon_trace}-{self.total_reserved_instances}-{waiting_times_str}.csv"
        df.to_csv(file_name, index=False)

    def save_results(
        self,
        cluster_type: str,
        scheduling_policy,
        carbon_policy,
        carbon_trace,
        task_trace,
        waiting_times_str,
    ):
        super().save_results(
            cluster_type,
            scheduling_policy,
            carbon_policy,
            carbon_trace,
            task_trace,
            waiting_times_str,
        )
        self.collect_slurm_results(
            cluster_type,
            scheduling_policy,
            carbon_policy,
            carbon_trace,
            task_trace,
            waiting_times_str,
        )

    def sleep(self):
        actual_sleep = max(1 - (time.time() - self.last_sleep), 0)
        time.sleep(actual_sleep)
        self.last_sleep = time.time()

    def done(self):
        return self.running_jobs == 0


class SlurmMonitor(Thread):
    def __init__(self, cluster: SlurmCluster, sleep_time=10):
        Thread.__init__(self)
        self.started = False
        self.details = []
        self.cluster = cluster
        self.sleep_time = sleep_time
        self.current_time = 0
        self.total_carbon_cost = 0
        self.total_dollar_cost = 0
        self.last_sleep = time.time()

    def node_stats(self) -> (int, int, int):
        power_on, power_on_spot = 0, 0
        try:
            nodes = pyslurm.node()
            new_node_dict = nodes.get()
            if new_node_dict:
                for k, node_details in new_node_dict.items():
                    if node_details["state"] not in KNOWN_STATES:
                        print(f"Unknown state {node_details['state']}")
                    if (
                        self.cluster.cluster_partition
                        not in node_details["partitions"][0]
                    ):
                        continue
                    if "POWER" not in node_details["state"]:
                        if "spot" in node_details["partitions"][0]:
                            power_on_spot += 1
                        else:
                            power_on += 1
        except Exception as e:
            print(f"Error - {e.args[0]}")
        return power_on, power_on_spot

    def running_jobs(self) -> int:
        running = 0
        reserved = self.cluster.total_reserved_instances
        try:
            start_time = datetime.utcfromtimestamp(
                self.cluster.experiment_start
            ).strftime("%Y-%m-%dT00:00:00")
            jobs = pyslurm.slurmdb_jobs()
            jobs_dict = jobs.get(
                starttime=start_time.encode("utf-8"),
            )
            if jobs_dict:
                for _, job_detail in jobs_dict.items():
                    if self.cluster.cluster_partition not in job_detail["partition"]:
                        continue
                    submit = int(job_detail["submit"] - self.cluster.experiment_start)
                    if submit < -1:
                        continue
                    if job_detail["state_str"] not in [
                        "COMPLETED",
                        "TIMEOUT",
                        "FAILED",
                    ]:
                        running += 1
                        reserved -= self.cluster.task_dict[
                            job_detail["jobname"]
                        ].reserved
                return running, reserved
            else:
                return 0
        except Exception as execption:
            print(f"Error:{execption.args[0]}")
            return 0

    def collect_info(self):
        power_on, power_on_spot = self.node_stats()
        running_jobs, reserved_idle = self.running_jobs()
        if reserved_idle < 0:
            print(f"How Come? {reserved_idle}")
        execution_carbon = self.cluster.carbon_model.df["carbon_intensity_avg"][
            self.current_time : self.current_time + self.sleep_time
        ].sum()

        self.total_carbon_cost += (power_on + power_on_spot) * execution_carbon
        self.total_dollar_cost += (
            max(power_on - reserved_idle, 0)
            * self.sleep_time
            * self.cluster.on_demand_cost
        )
        self.total_dollar_cost += (
            power_on_spot * self.sleep_time * self.cluster.spot_cost
        )

        self.cluster.running_jobs = running_jobs
        self.cluster.available_reserved_instances = reserved_idle
        self.details.append(
            [
                self.current_time,
                power_on,
                power_on_spot,
                power_on_spot + power_on,
                reserved_idle,
                running_jobs,
            ]
        )
        self.last_sleep = time.time()

    def run(self) -> None:
        self.started = True
        while self.started:
            with self.cluster.lock:
                self.collect_info()
            self.current_time += self.sleep_time
            actual_sleep = max(self.sleep_time - (time.time() - self.last_sleep), 0)
            time.sleep(actual_sleep)
