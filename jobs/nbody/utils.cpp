#include "main.h"

using namespace std;

double get_process_memory(void)
{
    struct rusage r_usage;

    int ret = getrusage(RUSAGE_SELF, &r_usage);
    if (ret == 0)
        return r_usage.ru_maxrss / 1024;
    else
        return 0;
}

void write_file(string results_folder, string name, int rank, vector<double> data)
{
    mkdir((results_folder + "logs/").data(), 0700);
    std::ofstream myFile(results_folder + "logs/" + name + "_" + to_string(rank) + ".csv");

    // Send the column name to the stream
    myFile << name << "\n";

    // Send data to the stream
    for (int i = 0; i < data.size(); ++i)
    {
        myFile << data.at(i) << "\n";
    }

    // Close the file
    myFile.close();
}
void save_metrics(string results_folder, int rank, std::vector<double> iteration_time, std::vector<double> checkpoint_time)
{
    write_file(results_folder, "iteration_time", rank, iteration_time);
    write_file(results_folder, "checkpoint_time", rank, checkpoint_time);
}

void save_progress(std::string results_folder, double time, double progress)
{
    std::ofstream myFile(results_folder + "progress.csv", std::ios_base::app);
    myFile << time << "," << progress << "\n";
    myFile.close();
}
