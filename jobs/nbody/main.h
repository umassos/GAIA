#include <sys/resource.h>
#include <unistd.h>
#include <CLI11.hpp>
#include <vector>

const int num_member = 7;

typedef struct
{
	// Location r_i = (x,y,z)
	double x;
	double y;
	double z;
	// Velocity v_i = (vx, vy, vz)
	double vx;
	double vy;
	double vz;
	// Mass
	double mass;
} Body;

double get_process_memory(void);
void save_metrics(std::string results_folder, int rank, std::vector<double> iteration_time, std::vector<double> checkpoint_time);
void save_progress(std::string results_folder, double time, double progress);