from typing import Callable
from carbon import CarbonModel
from task import TIME_FACTOR, Task
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


class SuspendSchedulingPolicy:
    """A Scheduling Policy that simulates a suspend and resume policy using an optimization approach.
    We refer to this policy in the paper as WaitAwhile.
    """

    def __init__(self, cluster: BaseCluster, carbon_model, optimal) -> None:
        self.cluster = cluster
        self.carbon_model: CarbonModel = carbon_model
        self.queue: PriorityQueue = PriorityQueue()
        self.optimal = optimal

    def compute_schedule_optimal(self, carbon_trace, task: Task):
        """Compute Suspend Resume Schedule WaitAwhile Optimal

        Args:
            carbon_trace (CarbonModel): Carbon Intensity model
            task (Task): current task

        Returns:
            List: execution schedule
        """
        job_length = task.task_length
        task_schedule = [0] * (task.task_length + task.waiting_time)
        assert len(task_schedule) == carbon_trace.shape[0]
        carbon_trace.sort_values(
            by=[
                "carbon_intensity_avg",
                "index",
            ],
            inplace=True,
        )
        for i, row in carbon_trace.iterrows():
            if job_length <= 0:
                break
            task_schedule[i] = 1
            job_length -= 1
        return task_schedule

    def compute_schedule_threshold(self, df, task: Task, mean_value):
        """Compute Suspend Resume Schedule WaitAwhile Threshold - Ecovisor

        Args:
            carbon_trace (CarbonModel): Carbon Intensity model
            task (Task): current task

        Returns:
            List: execution schedule
        """
        job_length = task.task_length
        task_schedule = [0] * (task.task_length + task.waiting_time)
        assert len(task_schedule) == df.shape[0]
        remaining_waiting = task.waiting_time
        for i in range(0, len(task_schedule)):
            if job_length <= 0:
                break
            if df["carbon_intensity_avg"][i] < mean_value or remaining_waiting <= 0:
                task_schedule[i] = 1
                job_length -= 1
            else:
                remaining_waiting -= 1
        assert job_length == 0
        return task_schedule

    def submit(self, current_time: int, task: Task):
        """Split Task to multiple jobs (suspend-resume) and submit them to GAIA Queue

        Args:
            current_time (int): time index
            task (Task): Task
        """
        try:
            c_model = self.carbon_model.subtrace(
                current_time, current_time + task.task_length + task.waiting_time
            )
            if self.optimal:
                schedule = self.compute_schedule_optimal(c_model.df, task)
            else:
                mean_value = self.carbon_model.df[
                    current_time : current_time + int(3600 / TIME_FACTOR * 24)
                ]["carbon_intensity_avg"].quantile(0.3)
                schedule = self.compute_schedule_threshold(c_model.df, task, mean_value)

            sub_tasks = []
            start_times = []
            tasks = 0
            i = 0
            while i < len(schedule):
                if schedule[i] == 0:
                    i += 1
                    continue
                start = i
                while i < len(schedule) and schedule[i] == 1:
                    i = i + 1
                subtask = Task(task.ID, current_time, i - start, task.CPUs)
                if not self.optimal:
                    subtask.task_length_class = task.task_length_class
                sub_tasks.append(subtask)
                start_times.append(start)
                tasks += 1
            assert tasks >= 1 and tasks == len(sub_tasks)
            if tasks == 1:
                self.queue.put(
                    QueueObject(task, current_time + start_times[0], task.arrival_time)
                )
            else:
                for i, subtask in enumerate(sub_tasks):
                    self.queue.put(
                        QueueObject(
                            subtask, current_time + start_times[i], task.arrival_time
                        )
                    )
        except:
            print("RealClusterCost: Submit Error")
            raise

    def execute(self, current_time):
        """Submit ready job/subjob to the simulated or real cluster queue

        Args:
            current_time (int): time index
        """
        queue = PriorityQueue()
        while not self.queue.empty():
            queue_object = self.queue.get()
            if current_time >= queue_object.max_start_time:
                self.cluster.submit(current_time, queue_object.task)
            else:
                queue.put(queue_object)
        self.queue = queue
        self.cluster.refresh_data(current_time)
