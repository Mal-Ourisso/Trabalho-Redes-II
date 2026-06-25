import socket
from threading import Thread
from utils import *

def run(proto):
    tcp = (proto == 'TCP')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM if tcp else socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', TCP_PORT if tcp else UDP_PORT))

    while True:
        if tcp:
            sock.listen(5)
            c, addr = sock.accept()
            req = c.recv(BUF).decode()
            if "GET" in req:
                f_name = req.split()[1].lstrip('/') or "index.html"
                try:
                    with open(f_name, 'rb') as f: data = f.read()
                    h = get_auth(MATRICULA, NOME)
                    c.sendall(f"HTTP/1.1 200 OK\r\nContent-Length: {len(data)}\r\nX-Custom-Auth: {h}\r\n\r\n".encode() + data)
                except:
                    c.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
            c.close()
        else:
            # Lógica RUDP (Server como transmissor)
            pkt, addr = sock.recvfrom(BUF)
            if SEP in pkt:
                head, load = pkt.split(SEP, 1)
                if "GET" in load.decode():
                    f_name = load.decode().split()[1] or "index.html"
                    with open(f_name, 'rb') as f: data = f.read()
                    
                    auth = get_auth(MATRICULA, NOME)
                    full = f"HTTP/1.1 200 OK\r\nContent-Length: {len(data)}\r\nX-Custom-Auth: {auth}\r\n\r\n".encode() + data
                    
                    seq, off = 1, 0
                    sock.settimeout(TIMEOUT_RUDP)
                    # Loop de retransmissão (Retries)
                    while off < len(full):
                        chunk = full[off:off+PAYLOAD]
                        pkt_send = make_pkt(auth, seq, chunk, (off + PAYLOAD >= len(full)))
                        ack_received = False
                        for _ in range(10): # Tentativas de retransmissão
                            sock.sendto(pkt_send, addr)
                            try:
                                ack, _ = sock.recvfrom(1024)
                                if ack.decode() == f"ACK:{seq}":
                                    seq = 1 - seq
                                    off += PAYLOAD
                                    ack_received = True
                                    break
                            except socket.timeout:
                                continue
                        if not ack_received: break
                    sock.settimeout(None)

if __name__ == "__main__":
    for p in ["TCP", "RUDP"]:
        Thread(target=run, args=(p,), daemon=True).start()
    input("Servidores rodando. Pressione Enter para sair.\n")