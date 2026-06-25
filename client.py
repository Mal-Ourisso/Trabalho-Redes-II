import socket, time, csv, argparse, os
from utils import *

def resolve(dom):
    start = time.time()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(TIMEOUT_DNS)
        req = f"ID:1001;NAME:{dom}".encode()
        for _ in range(3):
            try:
                s.sendto(req, (DNS_IP, DNS_PORT))
                d, _ = s.recvfrom(BUF)
                parts = dict(p.split(':') for p in d.decode().split(';') if ':' in p)
                if parts.get('IP') != "NOT_FOUND": return parts.get('IP'), time.time() - start
            except: continue
    return None, time.time() - start

def save_metrics(proto, arq, t_trans, t_dns, b_env, b_rec, size):
    vol = b_env + b_rec
    mbps = ((vol * 8) / t_trans / 1e6) if t_trans > 0 else 0
    overhead = vol - size
    
    file_path = "results/dados_consolidados.csv"
    file_exists = os.path.exists(file_path) and os.path.getsize(file_path) > 0
    
    with open(file_path, 'a', newline='') as f:
        writer = csv.writer(f)
        # Escreve o cabeçalho apenas se o arquivo não existir ou estiver vazio
        if not file_exists:
            writer.writerow([
                "Protocolo", "Arquivo_Solicitado", "Tamanho_Arquivo", 
                "Tempo_DNS", "Tempo_Transferencia", "Bytes_Enviados", 
                "Bytes_Recebidos", "Overhead", "Throughput"
            ])
        writer.writerow([proto, arq, size, t_dns, t_trans, b_env, b_rec, overhead, mbps])

def run(proto, arq):
    resultado_dns = resolve("meuservidor.ufpi.br")
    if not resultado_dns[0]: return
    ip, t_dns = resultado_dns
    
    dest = "temp_files/recebido.dat"
    t0 = time.time()
    
    is_tcp = (proto == 'TCP')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM if is_tcp else socket.SOCK_DGRAM)
    bytes_env, bytes_rec, file_size = 0, 0, 0
    
    if is_tcp:
        sock.connect((ip, TCP_PORT))
        req = f"GET {arq} HTTP/1.1\r\nHost: meuservidor.ufpi.br\r\n\r\n".encode()
        sock.sendall(req); bytes_env += len(req)
        with open(dest, "wb") as f:
            header_ok = False
            while d := sock.recv(BUF):
                bytes_rec += len(d)
                if not header_ok and b'\r\n\r\n' in d:
                    _, body = d.split(b'\r\n\r\n', 1)
                    f.write(body); file_size += len(body); header_ok = True
                elif header_ok:
                    f.write(d); file_size += len(d)
    else:
        # Lógica de recebimento RUDP com tratamento de confirmação
        sock.settimeout(TIMEOUT_RUDP * 10)
        req = f"GET {arq} HTTP/1.1\r\nHost: meuservidor.ufpi.br\r\n\r\n".encode()
        pacote_get = make_pkt(get_auth(MATRICULA, NOME), 0, req)
        
        done = False
        while not done:
            sock.sendto(pacote_get, (ip, UDP_PORT))
            bytes_env += len(pacote_get)
            
            seq_esperado, header_ok = 1, False
            file_size = 0
            with open(dest, "wb") as f:
                while True:
                    try:
                        pkt, addr = sock.recvfrom(BUF)
                        bytes_rec += len(pkt)
                        if SEP in pkt:
                            head_b, load = pkt.split(SEP, 1)
                            head_d = dict(p.split(':', 1) for p in head_b.decode().split(';') if ':' in p)
                            seq = int(head_d.get('Seq', -1))
                            eof = head_d.get('EOF') == 'True'
                            
                            if get_checksum(load) == head_d.get('Checksum'):
                                sock.sendto(f"ACK:{seq}".encode(), addr) # ACK para o servidor
                                bytes_env += len(f"ACK:{seq}".encode())
                                if seq == seq_esperado:
                                    if not header_ok and b'\r\n\r\n' in load:
                                        _, body = load.split(b'\r\n\r\n', 1)
                                        f.write(body); file_size += len(body); header_ok = True
                                    elif header_ok:
                                        f.write(load); file_size += len(load)
                                    seq_esperado = 1 - seq_esperado
                                if eof: 
                                    done = True
                                    break
                    except socket.timeout: break
        
    save_metrics(proto, arq.split('/')[-1], time.time() - t0, t_dns, bytes_env, bytes_rec, file_size)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--protocol', choices=['TCP', 'RUDP'], required=True)
    p.add_argument('--file', default='index.html')
    args = p.parse_args()
    run(args.protocol, args.file)