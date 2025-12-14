#include "metrics.hpp"
#include <cmath>
#include <cstdint>
#include <random>
#include <thread>

int main(int argc, char** argv) {
  if (argc < 4) return 2;
  std::string alg = argv[1];
  long long n     = std::atoll(argv[2]);
  uint64_t seed   = std::strtoull(argv[3], nullptr, 10);

  // Increase inner work so CPU time clears Windows' coarse 15.6ms tick
  // and avoids 0ms readings in very fast runs.
  constexpr int kInnerWork = 500000;
  uint64_t value = static_cast<uint64_t>(n > 1 ? n : 2);
  std::mt19937_64 rng(seed);

  BenchResult R{};
  R.alg = alg;
  R.n = n;
  R.seed = seed;
  R.threads = static_cast<int>(std::thread::hardware_concurrency());

  BenchTimer timer;
  timer.start();

  volatile uint64_t checksum = 0;
  while (value > 1) {
    for (int i = 0; i < kInnerWork; ++i) {
      checksum ^= (value ^ rng());
      checksum += (value | static_cast<uint64_t>(i));
      checksum = (checksum << 1) | (checksum >> 63);
    }
    value >>= 1;
  }

  timer.stop(R);
  if (checksum == 0xdeadbeefULL) std::puts("unlikely");

  print_json(R);
  return 0;
}
