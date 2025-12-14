cmake_minimum_required(VERSION 3.20)
project(bench_os_cpp CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_BUILD_TYPE Release)
add_compile_options(-O3 -march=native -DNDEBUG)

include_directories(include)

add_executable(qs algs/qs.cpp)
if (WIN32)
  target_link_libraries(qs psapi)
endif()

add_executable(mergesort algs/mergesort.cpp)
if (WIN32)
  target_link_libraries(mergesort psapi)
endif()

add_executable(linear_scan algs/linear_scan.cpp)
if (WIN32)
  target_link_libraries(linear_scan psapi)
endif()

add_executable(log_halving algs/log_halving.cpp)
if (WIN32)
  target_link_libraries(log_halving psapi)
endif()

add_executable(quadratic_bench algs/quadratic_bench.cpp)
if (WIN32)
  target_link_libraries(quadratic_bench psapi)
endif()
