#include "metrics.hpp"
#include <random>
#include <thread>
#include <vector>

int main(int argc, char** argv) {
  if (argc < 4) return 2;
  std::string alg = argv[1];
  long long n     = std::atoll(argv[2]);
  uint64_t seed   = std::strtoull(argv[3], nullptr, 10);

  if (n <= 0) return 3;
  const size_t N = static_cast<size_t>(n);
  std::vector<int> data(N);
  std::mt19937_64 rng(seed);
  for (auto& v : data) v = static_cast<int>(rng());

  BenchResult R{};
  R.alg = alg;
  R.n = n;
  R.seed = seed;
  R.threads = static_cast<int>(std::thread::hardware_concurrency());

  BenchTimer timer;
  timer.start();

  constexpr int kRepeats = 3; // stretch runtime to avoid 0ms CPU readings
  volatile long long checksum = 0;
  for (int r = 0; r < kRepeats; ++r) {
    for (size_t i = 0; i < N; ++i) {
      for (size_t j = 0; j < N; ++j) {
        checksum += (data[i] ^ data[j]);
        checksum -= (data[i] & data[j]);
      }
    }
  }

  timer.stop(R);
  if (checksum == 7) std::puts("unlikely");
  print_json(R);
  return 0;
}
