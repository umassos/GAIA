from abc import ABC, abstractmethod
import os

import pandas as pd
from carbon import CarbonModel
from task import Task, TIME_FACTOR
from threading import Lock

ON_DEMAND_COST_HOUR = 0.0624
SPOT_COST_HOUR = 0.01248  # 0.0341


class BaseCluster(ABC):
    def __init__(
        self,
        reserved_instances: int,
        carbon_model: CarbonModel,
        experiment_name: str,
        allow_spot: bool,
    ) -> None:
        """Common Cluster Configurations

        Args:
            reserved_instances (int): number of reserved instances
            carbon_model (CarbonModel): Carbon Intensity Model
            experiment_name (str): Hashed Configuration of tracking slurm tasks
            allow_spot (bool): Allow using Spot Instances
        """
        self.total_carbon_cost = 0
        self.total_dollar_cost = 0
        self.on_demand_cost = ON_DEMAND_COST_HOUR / (3600 / TIME_FACTOR)
        self.spot_cost = SPOT_COST_HOUR / (3600 / TIME_FACTOR)
        self.reserved_discount_rate = 0.4
        self.max_time = 0
        self.total_reserved_instances = reserved_instances
        self.available_reserved_instances = reserved_instances
        self.carbon_model = carbon_model
        self.details = []
        self.experiment_name = experiment_name
        self.runtime_allocation = [0] * carbon_model.df.shape[0]
        self.lock = Lock()
        self.allow_spot = allow_spot

    @abstractmethod
    def submit(self, current_time, task: Task):
        """Submit Tasks to the Cluster Queue

        Args:
            current_time (int): Time index
            task (Task): Submitted Task
        """
        pass

    @abstractmethod
    def refresh_data(self, current_time):
        """Release Allocated Resources, Only used in simulation

        Args:
            current_time (index): time index
        """
        pass

    def log_task(self, start_time, task: Task, dollar_cost, carbon, reason="completed"):
        waiting_time = start_time - task.arrival_time
        exit_time = start_time + task.task_length
        self.max_time = max(self.max_time, start_time)
        for i in range(start_time, exit_time + 1):
            self.runtime_allocation[i] += task.CPUs
        self.details.append(
            [
                task.ID,
                task.arrival_time,
                task.task_length,
                task.CPUs,
                task.task_length_class,
                task.CPUs_class,
                carbon,
                dollar_cost,
                start_time,
                waiting_time,
                exit_time,
                reason,
            ]
        )

    @abstractmethod
    def save_results(
        self,
        cluster_type: str,
        scheduling_policy: str,
        carbon_policy: str,
        carbon_trace: str,
        task_trace: str,
        waiting_times_str: str,
    ):
        """Save Simulation Results

        Args:
            cluster_type (str): cluster Type
            scheduling_policy (str): scheduling algorithm
            carbon_policy (str): carbon waiting policy
            carbon_trace (str): carbon trace name
            task_trace (str): task trace name
            waiting_times_str (str): waiting times per queue
        """
        self.total_dollar_cost += (
            self.total_reserved_instances
            * self.reserved_discount_rate
            * self.max_time
            * self.on_demand_cost
        )
        self.details.append(
            [
                -1,
                0,
                0,
                0,
                0,
                0,
                0,
                self.total_reserved_instances
                * self.reserved_discount_rate
                * self.max_time
                * self.on_demand_cost,
                0,
                0,
                0,
                0,
            ]
        )
        df = pd.DataFrame(
            self.details,
            columns=[
                "ID",
                "arrival_time",
                "length",
                "cpus",
                "length_class",
                "resource_class",
                "carbon_cost",
                "dollar_cost",
                "start_time",
                "waiting_time",
                "exit_time",
                "reason",
            ],
        )
        os.makedirs(f"results/{cluster_type}/{task_trace}/", exist_ok=True)
        file_name = f"results/{cluster_type}/{task_trace}/details-{scheduling_policy}-{self.carbon_model.carbon_start_index}-{carbon_policy}-{carbon_trace}-{self.total_reserved_instances}-{waiting_times_str}.csv"
        df.to_csv(file_name, index=False)
        runtime_df = pd.DataFrame(self.runtime_allocation, columns=["cpus"])
        runtime_df["time"] = range(self.carbon_model.df.shape[0])
        runtime_df["time"] //= 60
        runtime_df = runtime_df.groupby("time").mean().reset_index()
        file_name = f"results/{cluster_type}/{task_trace}/runtime-{scheduling_policy}-{self.carbon_model.carbon_start_index}-{carbon_policy}-{carbon_trace}-{self.total_reserved_instances}-{waiting_times_str}.csv"
        runtime_df.to_csv(file_name, index=False)

    @abstractmethod
    def sleep(self):
        """Sleep to allow execution, only effective in slurm clusters"""
        pass

    @abstractmethod
    def done(self):
        """Return True if cluster is idle, only effective in slurm clusters"""
        pass
