import argparse
import socket
import time
import os
import csv
from utils import *

def registrar_metricas(protocolo_nome, transfer_time, throughput_mbps, total_bytes_enviados):
    """Função de métricas para imprimir no terminal e gerar o CSV."""
    print("\n" + "="*40)
    print(f"MÉTRICAS DA APLICAÇÃO (CLIENTE {protocolo_nome})")
    print("="*40)
    print(f"Arquivo enviado   : {ARQUIVO_PARA_ENVIAR}")
    print(f"Volume de dados   : {total_bytes_enviados} bytes")
    print(f"Tempo de envio    : {transfer_time:.4f} segundos")
    print(f"Throughput        : {throughput_mbps:.4f} Mbps")
    print("="*40)

    arquivo_existe = os.path.isfile(DADOS_CONSOLIDADOS)
    
    with open(DADOS_CONSOLIDADOS, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not arquivo_existe:
            writer.writerow(["Protocolo", "Tempo_Segundos", "Throughput_Mbps", "Volume_Bytes"])
        writer.writerow([protocolo_nome, transfer_time, throughput_mbps, total_bytes_enviados])

def start_client(protocol):
    is_tcp = (protocol == 'tcp') # O código assume que se não é TCP é R-UDP
    sock_type = socket.SOCK_STREAM if is_tcp else socket.SOCK_DGRAM
    port = PORT_TCP if is_tcp else PORT_UDP
    protocolo_nome = "TCP" if is_tcp else "R-UDP"
    chunk_size = BUFFER_SIZE if is_tcp else PAYLOAD_SIZE

    if not os.path.exists(ARQUIVO_PARA_ENVIAR):
        print(f"[!] Erro: O arquivo '{ARQUIVO_PARA_ENVIAR}' não foi encontrado.")
        return

    auth_hash = gerar_hash_autenticacao(MATRICULA_ALUNO, NOME_ALUNO)
    total_bytes_enviados = 0
    seq = 0

    print(f"[*] Iniciando transferência {protocolo_nome} para {CLIENT_HOST}:{port}...")

    with socket.socket(socket.AF_INET, sock_type) as client_socket:
        
        if is_tcp:
            client_socket.connect((CLIENT_HOST, port))
            print("[+] Ligação estabelecida com sucesso!")
            header = f"X-Custom-Auth: {auth_hash}"
            header_bytes = header.encode('utf-8') + DELIMITER
            client_socket.sendall(header_bytes)
            print(f"[*] Cabeçalho de autenticação enviado: {header}")
        else:
            client_socket.settimeout(TIMEOUT)

        start_time = time.time()

        with open(ARQUIVO_PARA_ENVIAR, "rb") as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                
                if is_tcp:
                    client_socket.sendall(chunk)
                    total_bytes_enviados += len(chunk)
                
                else:
                    pacote = criar_pacote(auth_hash, seq, chunk)
                    ack_recebido = False

                    while not ack_recebido:
                        client_socket.sendto(pacote, (CLIENT_HOST, port))
                        try:
                            ack_data, _ = client_socket.recvfrom(1024)
                            if ack_data.decode('utf-8') == f"ACK:{seq}":
                                ack_recebido = True
                                total_bytes_enviados += len(chunk)
                                seq = 1 - seq # Alterna sequência
                        except socket.timeout:
                            pass

        # Envio do pacote EOF do protocolo R-UDP
        if not is_tcp:
            eof_pacote = criar_pacote(auth_hash, seq, b'', is_eof=True)
            ack_eof_recebido = False
            while not ack_eof_recebido:
                client_socket.sendto(eof_pacote, (CLIENT_HOST, port))
                try:
                    ack_data, _ = client_socket.recvfrom(1024)
                    if ack_data.decode('utf-8') == f"ACK:{seq}":
                        ack_eof_recebido = True
                except socket.timeout:
                    pass 

        end_time = time.time()

    transfer_time = end_time - start_time
    throughput_bps = (total_bytes_enviados * 8) / transfer_time if transfer_time > 0 else 0
    registrar_metricas(protocolo_nome, transfer_time, throughput_bps / 1_000_000, total_bytes_enviados)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente de Transferência de Arquivos")
    parser.add_argument('--protocol', choices=['tcp', 'rudp'], required=True, help="Protocolo: tcp ou rudp")
    args = parser.parse_args()

    if not os.path.exists(ARQUIVO_PARA_ENVIAR):
        print(f"[*] Criando arquivo de teste '{ARQUIVO_PARA_ENVIAR}' (1MB)...")
        with open(ARQUIVO_PARA_ENVIAR, "wb") as f:
            f.write(os.urandom(1024 * 1024))

    start_client(args.protocol)