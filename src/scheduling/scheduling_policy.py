from typing import Callable
from carbon import CarbonModel
from task import Task
from .carbon_waiting_policy import Schedule
from queue import PriorityQueue
from cluster import BaseCluster

class QueueObject:
    def __init__(self, task, max_start_time, priority) -> None:
        self.task = task
        self.max_start_time = max_start_time
        self.priority = priority

    def __lt__(self, other):
        return self.priority < other.priority

    def __str__(self):
        return str(self.x)

class SchedulingPolicy():
    def __init__(self, cluster:BaseCluster, carbon_model, compute_start_time, carbon_aware, cost_aware, spot_aware) -> None:
        self.cluster = cluster
        self.carbon_model: CarbonModel = carbon_model
        self.compute_start_time: Callable[[
            Task, CarbonModel], Schedule] = compute_start_time        
        self.queue: PriorityQueue = PriorityQueue()
        self.carbon_aware = carbon_aware
        self.cost_aware = cost_aware
        self.spot_aware = spot_aware

    def submit(self, current_time: int, task: Task):
        """Submit Job to GAIA Queue

        Args:
            current_time (int): time index
            task (Task): Task
        """
        if self.carbon_aware:
            try:
                c_model = self.carbon_model.subtrace(
                    current_time, current_time + max(task.task_length, task.expected_time) + task.waiting_time + 1)
                schedule = self.compute_start_time(task, c_model)
                self.queue.put(QueueObject(
                    task, schedule.actual_start_time(current_time), task.arrival_time))
            except:
                print("RealClusterCost: Submit Error")
                raise
        else:
            self.queue.put(QueueObject(
                task, task.waiting_time + current_time, task.arrival_time))

    def execute(self, current_time):
        """Submit ready job to the simulated or real cluster queue

        Args:
            current_time (int): time index
        """
        queue = PriorityQueue()
        while not self.queue.empty():
            queue_object = self.queue.get()
            if current_time >= queue_object.max_start_time:
                # Submit if ready
                self.cluster.submit(current_time, queue_object.task)
            elif self.cost_aware and not self.spot_aware and self.cluster.available_reserved_instances >= queue_object.task.CPUs:
                # Submit if work conserving (not spot) and available resources
                self.cluster.submit(current_time, queue_object.task)
            elif self.cost_aware and self.spot_aware and queue_object.task.task_length_class != "0-2" and self.cluster.available_reserved_instances >= queue_object.task.CPUs:
                # Submit if partial work conserving (long jobs only) and available resources
                self.cluster.submit(current_time, queue_object.task)
            else:
                queue.put(queue_object)
        self.queue = queue
        self.cluster.refresh_data(current_time)
        