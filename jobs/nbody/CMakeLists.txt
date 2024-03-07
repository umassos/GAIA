cmake_minimum_required(VERSION 3.10)
project(ElasticNbody)

set(CMAKE_CXX_COMPILER mpic++)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -g -std=c++11")

find_library(MPI Names mpi PATHS)
message(STATUS "MPI ${MPI}")
include_directories(.)

add_executable(elastic_nbody CLI11.hpp utils.cpp main.cpp)