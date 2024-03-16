from carbon import CarbonModel
from cluster import BaseCluster
from .scheduling_policy import SchedulingPolicy
from .suspend_scheduling_policy import SuspendSchedulingPolicy
from .carbon_waiting_policy import best_waiting_time, lowest_carbon_slot, oracle_carbon_slot,oracle_carbon_slot_waiting,average_carbon_slot_waiting


def create_scheduler(cluster: BaseCluster, scheduling_policy: str, carbon_policy, carbon_model: CarbonModel) -> SchedulingPolicy:
    if carbon_policy == "waiting":
        start_time_policy = best_waiting_time
    elif carbon_policy == "lowest":
        start_time_policy = lowest_carbon_slot
    elif carbon_policy == "oracle":
        start_time_policy = oracle_carbon_slot
    elif carbon_policy == "cst_oracle":
        start_time_policy = oracle_carbon_slot_waiting
    elif carbon_policy == "cst_average":
        start_time_policy = average_carbon_slot_waiting
    else:
        raise Exception("Unknown Carbon Policy")

    if scheduling_policy == "carbon":
        return SchedulingPolicy(cluster, carbon_model, start_time_policy, True, False, False)
    elif scheduling_policy == "carbon-spot":
        return SchedulingPolicy(cluster, carbon_model, start_time_policy, True, False, True)
    elif scheduling_policy == "carbon-cost":
        return SchedulingPolicy(cluster, carbon_model, start_time_policy, True, True, False)
    elif scheduling_policy == "carbon-cost-spot":
        return SchedulingPolicy(cluster, carbon_model, start_time_policy, True, True, True)
    elif scheduling_policy == "cost":
        return SchedulingPolicy(cluster, carbon_model, start_time_policy, False, True, False)
    elif scheduling_policy == "suspend-resume":
        return SuspendSchedulingPolicy(cluster, carbon_model, optimal=True)
    elif scheduling_policy == "suspend-resume-spot":
        return SuspendSchedulingPolicy(cluster, carbon_model, optimal=True)
    elif scheduling_policy == "suspend-resume-threshold":
        return SuspendSchedulingPolicy(cluster, carbon_model, optimal=False)
    elif scheduling_policy == "suspend-resume-spot-threshold":
        return SuspendSchedulingPolicy(cluster, carbon_model, optimal=False)
    else:
        raise Exception("Unknown Experiment Type")
