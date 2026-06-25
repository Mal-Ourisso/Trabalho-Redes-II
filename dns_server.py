import socket
from utils import DNS_PORT, BUF

hosts = {l.split()[0]: l.split()[1] for l in open('hosts.txt') if not l.startswith('#') and l.strip()}

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.bind(('0.0.0.0', DNS_PORT))
    while True:
        data, addr = s.recvfrom(BUF)
        parts = {p.split(':')[0]: p.split(':')[1] for p in data.decode().split(';')}
        ip = hosts.get(parts.get('NAME'), "NOT_FOUND") # type:ignore
        s.sendto(f"ID:{parts.get('ID')};NAME:{parts.get('NAME')};IP:{ip}".encode(), addr)