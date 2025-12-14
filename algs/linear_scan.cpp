#include "metrics.hpp"
#include <numeric>
#include <random>
#include <thread>
#include <vector>

int main(int argc, char** argv) {
  if (argc < 4) return 2;
  std::string alg = argv[1];
  long long n     = std::atoll(argv[2]);
  uint64_t seed   = std::strtoull(argv[3], nullptr, 10);

  if (n <= 0) return 3;
  std::mt19937_64 rng(seed);
  std::vector<int> buffer(static_cast<size_t>(n));
  for (auto& v : buffer) v = static_cast<int>(rng());

  BenchResult R{};
  R.alg = alg;
  R.n = n;
  R.seed = seed;
  R.threads = static_cast<int>(std::thread::hardware_concurrency());

  BenchTimer timer;
  timer.start();

  volatile long long sink = 0;
  constexpr int kPasses = 16; // ensure measurable wall-clock time for metrics
  for (int pass = 0; pass < kPasses; ++pass) {
    for (const auto value : buffer) {
      sink += value ^ pass;
      sink -= value & pass;
    }
  }

  timer.stop(R);
  // Prevent compiler from optimizing out the loop
  if (sink == 42) std::puts("unlikely");

  print_json(R);
  return 0;
}
