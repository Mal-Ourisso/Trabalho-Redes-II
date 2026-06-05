import argparse
import socket
import time
from utils import *

def start_server(protocol):
    is_tcp = (protocol == 'tcp') # O código assume que se não é TCP é R-UDP
    sock_type = socket.SOCK_STREAM if is_tcp else socket.SOCK_DGRAM
    port = PORT_TCP if is_tcp else PORT_UDP
    nome_arquivo = f"recebido_{protocol}.dat"

    with socket.socket(socket.AF_INET, sock_type) as server_socket:
        if is_tcp:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        server_socket.bind((SERVER_HOST, port))
        
        if is_tcp:
            server_socket.listen(5)
        
        print(f"[*] Servidor {protocol.upper()} escutando em {SERVER_HOST}:{port}...")

        while True:
            total_bytes_received = 0
            start_time = 0
            client_ip = None

            if is_tcp:
                conn, addr = server_socket.accept()
                client_ip = addr[0]
                active_socket = conn
                header_parsed = False
                buffer_residuo = b''
            else:
                active_socket = server_socket
                expected_seq = 0
                file_open = False

            with open(nome_arquivo, "wb") as file:
                
                if is_tcp:
                    start_time = time.time()
                    with conn:
                        while True:
                            data = active_socket.recv(BUFFER_SIZE)
                            if not data:
                                break
                            
                            total_bytes_received += len(data)

                            # Separa o cabeçalho X-Custom-Auth do arquivo real
                            if not header_parsed:
                                buffer_residuo += data
                                if DELIMITER in buffer_residuo:
                                    _, file_part = buffer_residuo.split(DELIMITER, 1)
                                    file.write(file_part)
                                    header_parsed = True
                            else:
                                file.write(data)
                
                else:
                    while True:
                        packet, addr = active_socket.recvfrom(BUFFER_SIZE)
                        client_ip = addr[0]
                        
                        if not file_open:
                            start_time = time.time()
                            file_open = True

                        if DELIMITER in packet:
                            header_bytes, payload = packet.split(DELIMITER, 1)
                            header_str = header_bytes.decode('utf-8')
                            
                            # Transforma a string de cabeçalhos em um dicionário para facilitar a leitura
                            header_dict = {
                                item.split(':', 1)[0].strip(): item.split(':', 1)[1].strip()
                                for item in header_str.split(';') if ':' in item
                            }
                            
                            seq = int(header_dict.get('Seq', -1))
                            checksum_recebido = header_dict.get('Checksum')
                            is_eof = header_dict.get('EOF') == 'True'

                            # Validação de integridade
                            if calcular_checksum(payload) != checksum_recebido:
                                continue # Ignora pacote corrompido

                            # Fim da transmissão
                            if is_eof:
                                active_socket.sendto(f"ACK:{seq}".encode('utf-8'), addr)
                                break 

                            # Controle de sequência e gravação
                            if seq == expected_seq:
                                file.write(payload)
                                total_bytes_received += len(payload)
                                active_socket.sendto(f"ACK:{seq}".encode('utf-8'), addr)
                                expected_seq = 1 - expected_seq
                            else:
                                # Pacote duplicado, reenvia o ACK
                                active_socket.sendto(f"ACK:{seq}".encode('utf-8'), addr)

            end_time = time.time()
            transfer_time = end_time - start_time
            throughput_bps = (total_bytes_received * 8) / transfer_time if transfer_time > 0 else 0
            
            print(f"[*] Arquivo {protocol.upper()} recebido de {client_ip}. Throughput: {(throughput_bps / 1_000_000):.4f} Mbps")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor de Transferência de Arquivos")
    parser.add_argument('--protocol', choices=['tcp', 'rudp'], required=True, help="Protocolo: tcp ou rudp")
    args = parser.parse_args()

    start_server(args.protocol)