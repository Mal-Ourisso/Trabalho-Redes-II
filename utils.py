import hashlib

DNS_IP, DNS_PORT = "10.0.0.2", 5053
TCP_PORT, UDP_PORT = 8080, 8081
BUF, PAYLOAD = 8192, 1024
TIMEOUT_RUDP, TIMEOUT_DNS = 0.5, 0.1
SEP = b'\r\n\r\n'

MATRICULA = "20199010480"
NOME = "Antônio Maurício Sousa Pinheiro"

def get_auth(m, n):
    return hashlib.sha256((m + n).encode()).hexdigest()

def get_checksum(d):
    return hashlib.md5(d).hexdigest()

def make_pkt(auth, seq, data, eof=False):
    chk = get_checksum(data)
    hdr = f"X-Custom-Auth:{auth};Seq:{seq};Checksum:{chk};EOF:{eof}"
    return hdr.encode() + SEP + data