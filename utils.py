import hashlib

# Configurações de Rede
SERVER_HOST = '0.0.0.0'
CLIENT_HOST = 'meu-servidor'
PORT_TCP = 5000
PORT_UDP = 5001
BUFFER_SIZE = 4096
PAYLOAD_SIZE = 1024
TIMEOUT = 0.5
DELIMITER = b'\r\n\r\n'

MATRICULA_ALUNO = "20199010480"
NOME_ALUNO = "Antônio Maurício Sousa Pinheiro"
ARQUIVO_PARA_ENVIAR = "teste_envio.txt"

DADOS_CONSOLIDADOS = "dados_consolidados.csv"

def gerar_hash_autenticacao(matricula, nome):
    """Gera o Hash SHA-256 para o cabeçalho."""
    return hashlib.sha256((matricula + nome).encode('utf-8')).hexdigest()

def calcular_checksum(dados):
    """Gera o Checksum MD5 do payload."""
    return hashlib.md5(dados).hexdigest()

def criar_pacote(auth_hash, seq, payload, is_eof=False):
    """Monta o pacote final com cabeçalhos estruturados para o R-UDP."""
    checksum = calcular_checksum(payload)
    header = f"X-Custom-Auth:{auth_hash};Seq:{seq};Checksum:{checksum};EOF:{is_eof}"
    return header.encode('utf-8') + DELIMITER + payload