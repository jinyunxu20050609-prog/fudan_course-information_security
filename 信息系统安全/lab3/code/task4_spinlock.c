#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <pthread.h>
#include <getopt.h>
#include <assert.h>
#include <sys/sysinfo.h>
#define DATA_SEPARATOR ","
#define PIN_THREADS
#define PIN_EVENLY

static uint64_t shared_counter = 0;
static uint64_t maxcounter = 100;
static uint64_t workers = 1;
static bool show_info = false, show_headers = false;

// 锁类型选择：0=pthread_spinlock, 1=custom_spinlock
#define USE_PTHREAD_SPINLOCK 0
#define USE_CUSTOM_SPINLOCK 1
static int lock_type = USE_PTHREAD_SPINLOCK;

// pthread_spinlock
static pthread_spinlock_t counter_spinlock;

// 自定义 spinlock
typedef struct {
    volatile int locked;
} custom_spinlock_t;
static custom_spinlock_t custom_lock = {0};

// 自定义 spinlock 函数
static inline void custom_spinlock_init(custom_spinlock_t *lock) {
    lock->locked = 0;
    __sync_synchronize(); // 内存屏障，确保初始化可见
}

static inline void custom_spinlock_lock(custom_spinlock_t *lock) {
    // 使用 test-and-set 原子操作自旋等待
    while (__sync_lock_test_and_set(&lock->locked, 1)) {
        // 自旋等待，使用 pause 指令降低功耗和减少总线竞争
        __asm__ __volatile__("pause" ::: "memory");
    }
    __sync_synchronize(); // 获取锁后的内存屏障
}

static inline void custom_spinlock_unlock(custom_spinlock_t *lock) {
    __sync_synchronize(); // 释放锁前的内存屏障
    __sync_lock_release(&lock->locked);
}

static inline void custom_spinlock_destroy(custom_spinlock_t *lock) {
    (void)lock; // 无操作
}

void* worker_func(void* args);
void parse_opts(int argc, char* const argv[]);

int main(int argc, char* const argv[]) {
	parse_opts(argc, argv);

	shared_counter = 0;
	
	// 初始化锁
	if (lock_type == USE_PTHREAD_SPINLOCK) {
		pthread_spin_init(&counter_spinlock, PTHREAD_PROCESS_PRIVATE);
	} else {
		custom_spinlock_init(&custom_lock);
	}
	
	int thread_args[workers];
	pthread_t threads[workers];
	uint64_t thread_counts[workers];

	//spawn worker threads
	const int cpus = get_nprocs();
	for (int i = 0; i < workers; ++i) {
		thread_args[i] = i;
		int result = pthread_create(&threads[i], NULL, worker_func, &thread_args[i]);
		assert(!result);

#ifdef PIN_THREADS

		//choose CPU core
#ifdef PIN_EVENLY
		const int core = i % cpus;
#else
		const int core = 0;
#endif

		//set affinity
		cpu_set_t cpuset;
		CPU_ZERO(&cpuset);
		CPU_SET(core, &cpuset);
		pthread_setaffinity_np(threads[i], sizeof(cpu_set_t), &cpuset);

#endif
	}

	//wait for all threads to complete
	long counts_total = 0;
	for (int i = 0; i < workers; ++i) {
		void *ret;
		int result = pthread_join(threads[i], &ret);
		assert(!result);
		thread_counts[i] = (uint64_t)(intptr_t)ret;
		counts_total += thread_counts[i]; //sum total number of updates
	}
	
	//destroy lock
	if (lock_type == USE_PTHREAD_SPINLOCK) {
		pthread_spin_destroy(&counter_spinlock);
	} else {
		custom_spinlock_destroy(&custom_lock);
	}

	//display statistics
	if (show_headers)
		printf("update ratio" DATA_SEPARATOR "average imbalance\n");

	if (show_info) {
		//print information about lost updates
		printf("%f" DATA_SEPARATOR, (double)counts_total / maxcounter);

		//print information about load imbalance
		uint64_t imbalance_total = 0;

		for (int i = 0; i < workers; i++) {
			const uint64_t expected_count = maxcounter / workers;
			uint64_t diff = (thread_counts[i] > expected_count) ? 
				(thread_counts[i] - expected_count) : 
				(expected_count - thread_counts[i]);
			imbalance_total += diff;
		}
		printf("%ld\n", imbalance_total / workers);
	}
	return 0;
}

void* worker_func(void* args) {
	int id = *((int*)args);

	uint64_t my_counter = 0;
	while (1) {
		// 获取锁
		if (lock_type == USE_PTHREAD_SPINLOCK) {
			pthread_spin_lock(&counter_spinlock);
		} else {
			custom_spinlock_lock(&custom_lock);
		}
		
		if (shared_counter >= maxcounter) {
			// 释放锁
			if (lock_type == USE_PTHREAD_SPINLOCK) {
				pthread_spin_unlock(&counter_spinlock);
			} else {
				custom_spinlock_unlock(&custom_lock);
			}
			break;
		}
		
		++shared_counter;
		++my_counter;
		
		// 释放锁
		if (lock_type == USE_PTHREAD_SPINLOCK) {
			pthread_spin_unlock(&counter_spinlock);
		} else {
			custom_spinlock_unlock(&custom_lock);
		}
	}

	pthread_exit((void*)(intptr_t)my_counter);
}

void parse_opts(int argc, char* const argv[]) {
	static struct option longopts[] = {
		{"maxcounter", required_argument, NULL, 'm'},
		{"workers", required_argument, NULL, 'w'},
		{"show-info", no_argument, NULL, 'i'},
		{"show-headers", no_argument, NULL, 'H'},
		{"custom-spinlock", no_argument, NULL, 'c'},
		{"help", no_argument, NULL, 'h'}
	};

	int longindex = 0;
	char flag = 0;
	while ((flag = getopt_long(argc, argv, "m:w:iHc", longopts, &longindex)) != -1) {
		switch (flag) {
		case 'm':
			maxcounter = atoll(optarg);
			break;
		case 'w':
			workers = atoll(optarg);
			break;
		case 'i':
			show_info = true;
			break;
		case 'H':
			show_headers = true;
			break;
		case 'c':
			lock_type = USE_CUSTOM_SPINLOCK;
			break;
		case 'h':
		default:
			printf("Usage: %s [--workers=n] [--maxcounter=n] [--show-info] [--show-headers] [--custom-spinlock]\n", argv[0]);
			exit(-1);
		}
	}
}