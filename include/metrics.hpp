// include/metrics.hpp
#pragma once
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <iostream>
#include <iomanip>

#if defined(_WIN32)
  #ifndef NOMINMAX
    #define NOMINMAX
  #endif
  #include <windows.h>
  #include <psapi.h>
#else
  #include <sys/resource.h>
  #include <unistd.h>
#endif

struct BenchResult {
  std::string alg;      // algorithm label, e.g. "qs"
  long long   n;        // input size
  uint64_t    seed;     // seed
  double      wall_ms;  // wall time
  double      cpu_user_ms;
  double      cpu_sys_ms;
  double      rss_peak_mib;
  int         threads;
};

struct BenchTimer {
  #if defined(_WIN32)
    FILETIME u0{}, s0{}, c0{}, e0{};
  #else
    rusage ru0{};
  #endif
  std::chrono::high_resolution_clock::time_point t0;

  void start() {
    t0 = std::chrono::high_resolution_clock::now();
    #if defined(_WIN32)
      HANDLE h = GetCurrentProcess();
      GetProcessTimes(h, &c0, &e0, &s0, &u0);
    #else
      getrusage(RUSAGE_SELF, &ru0);
    #endif
  }

  void stop(BenchResult& R) {
    auto t1 = std::chrono::high_resolution_clock::now();
    R.wall_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    #if defined(_WIN32)
      FILETIME u1{}, s1{}, c1{}, e1{};
      HANDLE h = GetCurrentProcess();
      GetProcessTimes(h, &c1, &e1, &s1, &u1);
      auto to_ms = [](const FILETIME& ft)->double {
        ULARGE_INTEGER li;
        li.LowPart  = ft.dwLowDateTime;
        li.HighPart = ft.dwHighDateTime;
        return (double)li.QuadPart / 10000.0; // 100ns → ms
      };
      R.cpu_user_ms = to_ms(u1) - to_ms(u0);
      R.cpu_sys_ms  = to_ms(s1) - to_ms(s0);

      PROCESS_MEMORY_COUNTERS_EX pmc{};
      if (GetProcessMemoryInfo(h, (PPROCESS_MEMORY_COUNTERS)&pmc, sizeof(pmc))) {
        R.rss_peak_mib = pmc.PeakWorkingSetSize / (1024.0 * 1024.0);
      } else {
        R.rss_peak_mib = 0.0;
      }
    #else
      rusage ru1{};
      getrusage(RUSAGE_SELF, &ru1);
      auto tv2ms = [](timeval tv)->double { return tv.tv_sec*1000.0 + tv.tv_usec/1000.0; };
      R.cpu_user_ms = tv2ms(ru1.ru_utime) - tv2ms(ru0.ru_utime);
      R.cpu_sys_ms  = tv2ms(ru1.ru_stime) - tv2ms(ru0.ru_stime);
      // ru_maxrss: KB on Linux (bytes on *BSD). On Linux → KB; convert to MiB:
      R.rss_peak_mib = (ru1.ru_maxrss * 1024.0) / (1024.0 * 1024.0);
    #endif
  }
};

inline void print_json(const BenchResult& R) {
  std::cout << std::fixed << std::setprecision(3);
  std::cout << "{"
            << "\"alg\":\"" << R.alg << "\","
            << "\"n\":" << R.n << ","
            << "\"seed\":" << R.seed << ","
            << "\"wall_ms\":" << R.wall_ms << ","
            << "\"cpu_user_ms\":" << R.cpu_user_ms << ","
            << "\"cpu_sys_ms\":" << R.cpu_sys_ms << ","
            << "\"rss_peak_mib\":" << R.rss_peak_mib << ","
            << "\"threads\":" << R.threads
            << "}\n";
}
