from carbon import CarbonModel
from .simulation_cluster import SimulationCluster
from .base_cluster import BaseCluster
from .base_cluster import ON_DEMAND_COST_HOUR


def create_cluster(cluster_type: str, scheduling_policy: str, carbon_model: CarbonModel, reserved_instances: int, experiment_name: str, waiting_times_str: str, cluster_partition: str):
    if cluster_type == "simulation":
        return SimulationCluster(reserved_instances, carbon_model, experiment_name, "spot" in scheduling_policy)
    elif cluster_type == "slurm":
        from .slurm_cluster import SlurmCluster
        if "spot" in scheduling_policy:
            return SlurmCluster(reserved_instances, carbon_model, experiment_name, cluster_partition, True)
        else:
            return SlurmCluster(reserved_instances, carbon_model, experiment_name, cluster_partition, False)

    else:
        raise Exception("Not Implemented")
