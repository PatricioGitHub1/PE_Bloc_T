#include "metrics.hpp"
#include <random>
#include <thread>
#include <algorithm>
#include <vector>

// Merge sort implementation
template<typename T>
void merge(std::vector<T>& arr, long long left, long long mid, long long right) {
    long long n1 = mid - left + 1;
    long long n2 = right - mid;
    
    std::vector<T> L(n1), R(n2);
    
    for (long long i = 0; i < n1; i++)
        L[i] = arr[left + i];
    for (long long j = 0; j < n2; j++)
        R[j] = arr[mid + 1 + j];
    
    long long i = 0, j = 0, k = left;
    
    while (i < n1 && j < n2) {
        if (L[i] <= R[j]) {
            arr[k] = L[i];
            i++;
        } else {
            arr[k] = R[j];
            j++;
        }
        k++;
    }
    
    while (i < n1) {
        arr[k] = L[i];
        i++;
        k++;
    }
    
    while (j < n2) {
        arr[k] = R[j];
        j++;
        k++;
    }
}

template<typename T>
void mergeSort(std::vector<T>& arr, long long left, long long right) {
    if (left < right) {
        long long mid = left + (right - left) / 2;
        mergeSort(arr, left, mid);
        mergeSort(arr, mid + 1, right);
        merge(arr, left, mid, right);
    }
}

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

  if (!v.empty()) {
    mergeSort(v, 0, static_cast<long long>(v.size()) - 1);
  }

  T.stop(R);
  print_json(R);
  return 0;
}
