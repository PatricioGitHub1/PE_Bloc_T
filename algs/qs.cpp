#include "metrics.hpp"
#include <random>
#include <thread>
#include <algorithm>
#include <vector>

int main(int argc, char** argv) {
  // args: alg n seed
  if (argc < 4) return 2;
  std::string alg = argv[1];
  long long n     = std::atoll(argv[2]);
  uint64_t seed   = std::strtoull(argv[3], nullptr, 10);

  std::mt19937_64 rng(seed);
  std::vector<int> v(n);
  for (auto& x : v) x = (int)(rng());

  BenchResult R{};
  R.alg = alg; R.n = n; R.seed = seed;
  R.threads = (int)std::thread::hardware_concurrency();

  BenchTimer T; T.start();

  std::sort(v.begin(), v.end()); // actual sorting work

  T.stop(R);
  print_json(R);
  return 0;
}
