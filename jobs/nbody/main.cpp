#include <cstdio>
#include <cstring>
#include <iostream>
#include "mpi.h"
#include "main.h"
#include <math.h>

using namespace std;

MPI_Datatype TYPE_BODY = NULL;
MPI_Status status;

void create_type()
{
	MPI_Aint blockoffsets[7];
	blockoffsets[0] = offsetof(Body, x);
	blockoffsets[1] = offsetof(Body, y);
	blockoffsets[2] = offsetof(Body, z);
	blockoffsets[3] = offsetof(Body, vx);
	blockoffsets[4] = offsetof(Body, vy);
	blockoffsets[5] = offsetof(Body, vz);
	blockoffsets[6] = offsetof(Body, mass);
	int blocklength[7] = {1, 1, 1, 1, 1, 1, 1};
	MPI_Datatype types[7] = {MPI_DOUBLE, MPI_DOUBLE, MPI_DOUBLE, MPI_DOUBLE, MPI_DOUBLE, MPI_DOUBLE, MPI_DOUBLE};

	MPI_Type_create_struct(num_member, blocklength, blockoffsets, types, &TYPE_BODY);
	MPI_Type_commit(&TYPE_BODY);
}

long get_rank_bodies(long total_bodies, int rank, int size)
{
	long length, watershed, base;
	watershed = total_bodies % size;
	base = total_bodies / size;

	if (rank < watershed)
	{
		length = base + 1;
	}
	else
	{
		length = base;
	}
	return length;
}

long create_bodies_static(Body *bodies, long total_bodies, int rank, int size, long start)
{
	long rank_bodies = get_rank_bodies(total_bodies, rank, size);
	long n;
	for (long i; i < rank_bodies; i++)
	{
		n = start + i;
		bodies[i].x = n;
		bodies[i].y = n;
		bodies[i].z = n;

		// Intialize velocities
		bodies[i].vx = n * n;
		bodies[i].vy = n * n;
		bodies[i].vz = n * n;

		// Initialize masses so that total mass of system is constant
		// regardless of how many bodies are simulated
		bodies[i].mass = 1.0 / total_bodies;
	}
	return n;
}

// The master is the one which initializes.
void initialize_static(Body *local, Body *outgoing, int rank, int size, long total_bodies, long node_max)
{
	if (rank == 0)
	{
		long n;
		// Rank 0 generates for itself
		n = create_bodies_static(local, total_bodies, rank, size, 0);
		// Rank 0 generates for rest of ranks
		for (int i = 1; i < size; i++)
		{
			n = create_bodies_static(outgoing, total_bodies, i, size, n + 1);
			MPI_Send(outgoing, node_max, TYPE_BODY, i, 1, MPI_COMM_WORLD);
		}
	}
	else
	{
		// Rank i receives particles from Rank 0
		MPI_Recv(local, node_max, TYPE_BODY, 0, 1, MPI_COMM_WORLD, &status);
	}
}

int initialize_restore(Body *local, Body *outgoing, int rank, int size, long total_bodies, long node_max, string results_folder, int *start_iteration)
{
	if (rank == 0)
	{
		string checkpoint_file = results_folder + "checkpoint.dat";
		cout << "Reloading from " << checkpoint_file << endl;
		ifstream rf(checkpoint_file, ios::out | ios::binary);
		if (!rf)
		{
			cout << "Cannot open file!" << endl;
			return 1;
		}
		long rank_bodies = get_rank_bodies(total_bodies, rank, size);
		rf.read((char *)start_iteration, sizeof(int));
		*start_iteration = *start_iteration  + 1;
		for (int i = 0; i < rank_bodies; i++)
			rf.read((char *)&local[i], sizeof(Body));
		for (int i = 1; i < size; i++)
		{
			rank_bodies = get_rank_bodies(total_bodies, i, size);
			for (int i = 0; i < rank_bodies; i++)
				rf.read((char *)&outgoing[i], sizeof(Body));
			MPI_Send(start_iteration, 1, MPI_INT, i, 1, MPI_COMM_WORLD);
			MPI_Send(outgoing, node_max, TYPE_BODY, i, 1, MPI_COMM_WORLD);
		}
		rf.close();
		if (!rf.good())
		{
			cout << "Error occurred at reading time!" << endl;
			return 1;
		}
	}
	else
	{
		MPI_Recv(start_iteration, 1, MPI_INT, 0, 1, MPI_COMM_WORLD, &status);
		MPI_Recv(local, node_max, TYPE_BODY, 0, 1, MPI_COMM_WORLD, &status);
	}

	return 0;
}

int initialize(Body *local, Body *outgoing, int rank, int size, long total_bodies, long node_max, bool restore, string results_folder, int *start_iteration)
{
	string checkpoint_file = results_folder + "checkpoint.dat";
	ifstream rf(checkpoint_file, ios::out | ios::binary);
	if (!rf | !restore)
	{
		*start_iteration = 0;
		initialize_static(local, outgoing, rank, size, total_bodies, node_max);
		return 0;
	}
	else
		return initialize_restore(local, outgoing, rank, size, total_bodies, node_max, results_folder, start_iteration);
}

void compute_velocity(Body *local, Body *incoming, double dt, long nlocal, long nremote)
{

	double G = 1.0;
	double softening = 0.1;
	for (long i = 0; i < nlocal; i++)
	{

		double Fx = 0.0;
		double Fy = 0.0;
		double Fz = 0.0;

		for (long j = 0; j < nremote; j++)
		{

			double dx = incoming[j].x - local[i].x;
			double dy = incoming[j].y - local[i].y;
			double dz = incoming[j].z - local[i].z;

			double distance = sqrt(dx * dx + dy * dy + dz * dz + softening * softening);
			double distance_cubed = distance * distance * distance;

			double m_j = local[j].mass;
			double mGd = G * m_j / distance_cubed;
			Fx += mGd * dx;
			Fy += mGd * dy;
			Fz += mGd * dz;
		}

		local[i].vx += dt * Fx;
		local[i].vy += dt * Fy;
		local[i].vz += dt * Fz;
	}
}

void do_iteration(Body *local, Body *incoming, Body *outgoing, long total_bodies, long node_max, long local_bodies, int rank, int size, double dt)
{

	Body *temp;
	// Copy local particles to remote buffer
	memcpy(incoming, local, local_bodies * sizeof(Body));

	for (int i = 0; i < size; i++)
	{
		// Now it's time to calculate particles in Rank i and Rank i+rank
		long nremote = get_rank_bodies(total_bodies, (i + rank) % size, size);
		// Compute new forces & velocities for all particles
		compute_velocity(local, incoming, dt, local_bodies, nremote);
		// Switch buffers: incomings <=> outgoings
		temp = incoming;
		incoming = outgoing;
		outgoing = temp;
		// Roll the buffer: (i-1) <= i <= (i+1)
		int prev = (rank - 1 + size) % size;
		int next = (rank + 1) % size;
		MPI_Sendrecv(
			outgoing, node_max, TYPE_BODY, prev, 1,
			incoming, node_max, TYPE_BODY, next, 1,
			MPI_COMM_WORLD, MPI_STATUS_IGNORE);
	}
	for (int i = 0; i < local_bodies; i++)
	{
		local[i].x += local[i].vx * dt;
		local[i].y += local[i].vy * dt;
		local[i].z += local[i].vz * dt;
	}
}

void printBodies(Body *bodies, long rank_bodies)
{
	for (long i; i < rank_bodies; i++)
	{
		cout << i << ": m = " << bodies[i].mass << ". P = [" << bodies[i].x << "," << bodies[i].y << "," << bodies[i].z << "]";
		cout << ", V = [" << bodies[i].vx << "," << bodies[i].vy << "," << bodies[i].vz << "]" << endl;
	}
}

void collect_print(Body *local, Body *incoming, int rank, int size, long node_max, long total_bodies)
{
	if (rank == 0)
	{
		long rank_bodies = get_rank_bodies(total_bodies, rank, size);
		printBodies(local, rank_bodies);
		for (int i = 1; i < size; i++)
		{

			MPI_Recv(incoming, node_max, TYPE_BODY, i, 1, MPI_COMM_WORLD, &status);
			rank_bodies = get_rank_bodies(total_bodies, i, size);
			printBodies(incoming, rank_bodies);
		}
	}
	else
	{
		// Rank i receives particles from Rank 0
		MPI_Send(local, node_max, TYPE_BODY, 0, 1, MPI_COMM_WORLD);
	}
}

int checkpoint_state(Body *local, Body *incoming, int rank, int size, long node_max, long total_bodies, int iteration, string results_folder)
{
	if (rank == 0)
	{
		// Rank 0 is responsible for checkpoint
		string checkpoint_file = results_folder + "checkpoint.dat";
		ofstream wf(checkpoint_file, ios::out | ios::binary);
		if (!wf)
		{
			cout << "Cannot open file!" << endl;
			return 1;
		}
		long rank_bodies = get_rank_bodies(total_bodies, rank, size);

		wf.write((char *)&iteration, sizeof(int));

		for (int i = 0; i < rank_bodies; i++)
			wf.write((char *)&local[i], sizeof(Body));

		// Do other ranks
		for (int i = 1; i < size; i++)
		{
			MPI_Recv(incoming, node_max, TYPE_BODY, i, 1, MPI_COMM_WORLD, &status);
			rank_bodies = get_rank_bodies(total_bodies, i, size);
			for (int i = 0; i < rank_bodies; i++)
				wf.write((char *)&incoming[i], sizeof(Body));
		}

		wf.close();
		if (!wf.good())
		{
			cout << "Error occurred at writing time!" << endl;
			return 1;
		}
	}
	else
	{
		// Rank i receives particles from Rank 0
		MPI_Send(local, node_max, TYPE_BODY, 0, 1, MPI_COMM_WORLD);
	}
	return 0;
}

int main(int argc, char *argv[])
{
	int rank, size;
	long total_bodies = 10;
	bool restore{false};
	bool print_result{false};
	int checkpoint_interval = 1;
	int total_iterations = 10;
	string results_folder = "./results/";

	// Argument Management
	CLI::App app{"Elastic Nbody Simulation"};
	// Define options
	app.add_option("-b,--total-bodies", total_bodies, "Total Bodies");
	app.add_flag("-r,--restore", restore, "Restore");
	app.add_flag("-p,--print", restore, "Print inital and final values");
	app.add_option("-c,--checkpoint-interval", checkpoint_interval, "Checkpoint interval");
	app.add_option("-f,--results-folder", results_folder, "Results Folder");
	app.add_option("-i,--iterations", total_iterations, "Total number of iterations");
	CLI11_PARSE(app, argc, argv);

	// Performance counters
	vector<double> checkpoint_time = {};
	vector<double> iteration_time = {};

	// MPI initialization
	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	MPI_Comm_size(MPI_COMM_WORLD, &size);
	create_type();

	mkdir(results_folder.data(), 0700);
	results_folder = results_folder + to_string(total_bodies) + "/";
	// Fix folder to keep logs in the same folder
	//mkdir(results_folder.data(), 0700);
	//results_folder = results_folder + to_string(size) + "/";
	mkdir(results_folder.data(), 0700);

	long node_max = total_bodies / size + 1;
	long local_bodies = get_rank_bodies(total_bodies, rank, size);
	cout << "Hello, I am " << rank << " out of " << size << " and have " << local_bodies << endl;

	Body *local = (Body *)calloc(node_max, sizeof(Body));
	Body *outgoing = (Body *)calloc(node_max, sizeof(Body));
	Body *incoming = (Body *)calloc(node_max, sizeof(Body));
	int start_iteration = 0;

	if (initialize(local, outgoing, rank, size, total_bodies, node_max, restore, results_folder, &start_iteration))
	{
		cout << "Aborting Program" << endl;
		MPI_Abort(MPI_COMM_WORLD, 1);
	}

	if (rank == 0)
	{
		cout << "Starting from iteration " << start_iteration << endl;
	}
	if (print_result)
		collect_print(local, incoming, rank, size, node_max, total_bodies);
	double dt = 1;


	for (int i = start_iteration; i < total_iterations; i++)
	{
		double start = MPI_Wtime();
		do_iteration(local, incoming, outgoing, total_bodies, node_max, local_bodies, rank, size, dt);
		double stop = MPI_Wtime();
		iteration_time.push_back(stop - start);
		if (rank == 0)
		{
			save_progress(results_folder, MPI_Wtime(), (i + 1) * 100.0 / total_iterations);
			cout << "Iteration: " << i;
			cout << " Time [s]: " << stop - start << endl;
		}
		if (i % checkpoint_interval == 0)
		{
			if (rank == 0)
			{
				cout << "checkpointing" << endl;
			}
			double start = MPI_Wtime();
			if (checkpoint_state(local, incoming, rank, size, node_max, total_bodies, i, results_folder))
			{
				cout << "Aborting Program" << endl;
				MPI_Abort(MPI_COMM_WORLD, 1);
			}
			double stop = MPI_Wtime();
			checkpoint_time.push_back(stop - start);
		}
	}

	if (rank == 0)
	{
		cout << "Simulation is done " << endl;
	}
	if (print_result)
		collect_print(local, incoming, rank, size, node_max, total_bodies);

	save_metrics(results_folder, rank, iteration_time, checkpoint_time);
	MPI_Type_free(&TYPE_BODY);
	free(local);
	free(incoming);
	free(outgoing);
	MPI_Finalize();
}
