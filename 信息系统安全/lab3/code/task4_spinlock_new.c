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

// 编译器优化提示
#define likely(x)   __builtin_expect(!!(x), 1)
#define unlikely(x) __builtin_expect(!!(x), 0)

static uint64_t shared_counter = 0;
static uint64_t maxcounter = 100;
static uint64_t workers = 1;
static bool show_info = false, show_headers = false;

// ============================================
// 优化的自定义 Spinlock 实现
// ============================================
typedef struct {
    volatile int locked;
} custom_spinlock_t;

static custom_spinlock_t counter_lock = {0};

// 初始化 spinlock（优化：移除不必要的内存屏障）
static inline void custom_spinlock_init(custom_spinlock_t *lock) {
    // 静态初始化已经保证为0，无需额外同步
    lock->locked = 0;
}

// 高度优化的 lock 函数
// 使用最简化的高效实现，参考 Linux 内核和现代 CPU 优化
static inline void custom_spinlock_lock(custom_spinlock_t *lock) {
    // 快速路径优化：使用 likely 提示编译器优化
    // 大多数情况下锁是空闲的，这个分支会被优化
    if (likely(__sync_lock_test_and_set(&lock->locked, 1) == 0)) {
        return; // 成功获取锁，直接返回（避免进入循环）
    }
    
    // 慢速路径：自旋等待
    // 使用 pause 指令优化自旋等待
    // pause 指令在 x86/x86_64 上的优势：
    // 1. 降低 CPU 功耗（约 10-30 倍）
    // 2. 减少内存总线竞争（避免缓存行乒乓）
    // 3. 提高超线程性能（让出执行单元给其他线程）
    // 4. 在 Skylake+ 架构上延迟约 140 周期（足够让其他线程执行）
    do {
        __asm__ __volatile__("pause" ::: "memory");
    } while (__sync_lock_test_and_set(&lock->locked, 1));
    
    // __sync_lock_test_and_set 本身包含 acquire 语义
    // 无需额外的内存屏障
}

// 高度优化的 unlock 函数
static inline void custom_spinlock_unlock(custom_spinlock_t *lock) {
    // __sync_lock_release 是最轻量级的释放操作
    // 它包含 release 语义，确保所有写操作在释放前完成
    __sync_lock_release(&lock->locked);
}

// 销毁 spinlock（无操作，但保留接口一致性）
static inline void custom_spinlock_destroy(custom_spinlock_t *lock) {
    (void)lock;
}

void* worker_func(void* args);
void parse_opts(int argc, char* const argv[]);

int main(int argc, char* const argv[]) {
	parse_opts(argc, argv);

	shared_counter = 0;
	
	// 初始化自定义 spinlock
	custom_spinlock_init(&counter_lock);
	
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
	custom_spinlock_destroy(&counter_lock);

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
		// 获取自定义 spinlock
		custom_spinlock_lock(&counter_lock);
		
		// 检查是否达到目标值
		if (shared_counter >= maxcounter) {
			custom_spinlock_unlock(&counter_lock);
			break;
		}
		
		// 临界区：快速更新计数器（最小化临界区）
		++shared_counter;
		++my_counter;
		
		// 立即释放锁（减少锁持有时间，提高并发性）
		custom_spinlock_unlock(&counter_lock);
	}

	pthread_exit((void*)(intptr_t)my_counter);
}

void parse_opts(int argc, char* const argv[]) {
	static struct option longopts[] = {
		{"maxcounter", required_argument, NULL, 'm'},
		{"workers", required_argument, NULL, 'w'},
		{"show-info", no_argument, NULL, 'i'},
		{"show-headers", no_argument, NULL, 'H'},
		{"help", no_argument, NULL, 'h'}
	};

	int longindex = 0;
	char flag = 0;
	while ((flag = getopt_long(argc, argv, "m:w:iH", longopts, &longindex)) != -1) {
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
		case 'h':
		default:
			printf("Usage: %s [--workers=n] [--maxcounter=n] [--show-info] [--show-headers]\n", argv[0]);
			exit(-1);
		}
	}
}

