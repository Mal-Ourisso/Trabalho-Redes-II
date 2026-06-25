import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import subprocess
import glob

RESULTS_DIR = "results/"
GRAFICOS_DIR = os.path.join(RESULTS_DIR, "graficos")
CSV_PATH = os.path.join(RESULTS_DIR, "dados_consolidados.csv")
PCAP_DIR = "capturas/"
DOSSIE_PATH = os.path.join(RESULTS_DIR, "check_pcap.txt")

os.makedirs(GRAFICOS_DIR, exist_ok=True)

def sort_key_tamanho(tamanho_str):
    if "MB" in tamanho_str:
        return float(tamanho_str.replace("MB", "").strip()) * 1048576
    elif "KB" in tamanho_str:
        return float(tamanho_str.replace("KB", "").strip()) * 1024
    elif "BYTE" in tamanho_str:
        return float(tamanho_str.split()[0].strip())
    else:
        return float(tamanho_str)
    
def formatar_bytes(b):
    try:
        b = float(b)
        if b >= 1048576:
            val = b / 1048576
            return f"{int(val) if val.is_integer() else round(val, 2)} MB"
        elif b >= 1024:
            val = b / 1024
            return f"{int(val) if val.is_integer() else round(val, 2)} KB"
        else:
            return f"{int(b)} Bytes"
    except Exception:
        return str(b)

def ler_config_env():
    num_runs = 10
    with open("config.env", "r") as f:
        for linha in f:
            linha = linha.strip()
            if linha.startswith("NUM_RUNS="):
                num_runs = int(linha.split("=")[1])
                break
    return num_runs

def carregar_dados_e_inferir_contexto(num_runs):
    colunas = [
        'Protocolo', 'Arquivo_Solicitado', 'Tamanho_Arquivo', 
        'Tempo_DNS', 'Tempo_Transferencia', 'Bytes_Enviados', 
        'Bytes_Recebidos', 'Overhead', 'Throughput'
    ]
    
    df = pd.read_csv(CSV_PATH, names=colunas, header=0)
    
    df['Protocolo'] = df['Protocolo'].str.strip().str.lower()
    df['Tempo_Total'] = df['Tempo_DNS'] + df['Tempo_Transferencia']
    df['Tamanho_Arquivo'] = df['Tamanho_Arquivo'].apply(formatar_bytes)

    num_arquivos = df['Tamanho_Arquivo'].nunique()
    linhas_por_cenario = num_runs * 2 * num_arquivos
    
    perdas = []
    for i in range(len(df)):
        if i < linhas_por_cenario:
            perdas.append(0)
        elif i < 2 * linhas_por_cenario:
            perdas.append(5)
        else:
            perdas.append(10)
            
    df['Perda'] = perdas
    return df

def gerar_tabelas_resumo(df):
    resumo = df.groupby(['Protocolo', 'Perda', 'Tamanho_Arquivo'])[['Tempo_DNS', 'Tempo_Transferencia', 'Tempo_Total', 'Overhead', 'Throughput']].mean().reset_index()
    resumo = resumo.round(3)
    
    caminho_tabela = os.path.join(RESULTS_DIR, "resumo_medias.csv")
    resumo.to_csv(caminho_tabela, index=False)
    return resumo

def plot_tempo_total(resumo):
    arquivos = sorted(resumo['Tamanho_Arquivo'].unique(), key=sort_key_tamanho)
    perdas = sorted(resumo['Perda'].unique())
    
    fig, axes = plt.subplots(1, len(arquivos), figsize=(6 * len(arquivos), 6), sharey=False)
    fig.suptitle('Tempo Total de Carregamento (DNS + Transferência) - TCP vs R-UDP', fontsize=16, y=1.05)
    
    for i, arq in enumerate(arquivos):
        ax = axes[i] if len(arquivos) > 1 else axes
        df_arq = resumo[resumo['Tamanho_Arquivo'] == arq]
        
        tcp_times = df_arq[df_arq['Protocolo'] == 'tcp']['Tempo_Total'].values
        rudp_times = df_arq[df_arq['Protocolo'] == 'rudp']['Tempo_Total'].values
        
        x = np.arange(len(perdas))
        width = 0.35
        
        if len(tcp_times) < len(x): tcp_times = np.pad(tcp_times, (0, len(x) - len(tcp_times)))
        if len(rudp_times) < len(x): rudp_times = np.pad(rudp_times, (0, len(x) - len(rudp_times)))
        
        bars1 = ax.bar(x - width/2, tcp_times, width, label='TCP', color='#1f77b4') 
        bars2 = ax.bar(x + width/2, rudp_times, width, label='R-UDP', color='#ff7f0e') 
        
        ax.bar_label(bars1, fmt='%.2f', padding=3, fontsize=9)
        ax.bar_label(bars2, fmt='%.2f', padding=3, fontsize=9)
        
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=2, frameon=False, fontsize=9)
        ax.set_ylim(0, max(tcp_times.max(), rudp_times.max()) * 1.3)
        
        ax.set_title(f'Tamanho: {arq}')
        ax.set_xlabel('Perda de Pacotes (%)')
        ax.set_ylabel('Tempo (Segundos)')
        ax.set_xticks(x)
        ax.set_xticklabels([f"{p}%" for p in perdas])
        ax.grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()
    plt.savefig(os.path.join(GRAFICOS_DIR, "tempo_total.png"), bbox_inches='tight', dpi=300)
    plt.close()

def plot_dns_vs_http(resumo):
    arquivos = sorted(resumo['Tamanho_Arquivo'].unique(), key=sort_key_tamanho)
    
    fig, axes = plt.subplots(1, len(arquivos), figsize=(7 * len(arquivos), 6), sharey=False)
    fig.suptitle('Tempo de DNS vs Tempo de Transferência', fontsize=16, y=1.05)
    
    for i, arq in enumerate(arquivos):
        ax = axes[i] if len(arquivos) > 1 else axes
        df_arq = resumo[resumo['Tamanho_Arquivo'] == arq].sort_values('Perda')
        
        labels = [f"{row['Protocolo'].upper()}\n({row['Perda']}%)" for _, row in df_arq.iterrows()]
        dns_times = df_arq['Tempo_DNS'].values
        transf_times = df_arq['Tempo_Transferencia'].values
        
        bars1 = ax.bar(labels, dns_times, label='Tempo DNS', color='#1f77b4') 
        bars2 = ax.bar(labels, transf_times, bottom=dns_times, label='Tempo Transferência', color='#ff7f0e') 
        
        totais = [f'{(d + t):.2f}' for d, t in zip(dns_times, transf_times)]
        ax.bar_label(bars2, labels=totais, padding=3, fontsize=9)
        
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=2, frameon=False, fontsize=9)
        ax.set_ylim(0, (dns_times + transf_times).max() * 1.3)
        
        ax.set_title(f'Tamanho: {arq}')
        ax.set_ylabel('Tempo (Segundos)')
        ax.tick_params(axis='x', rotation=0)
        ax.grid(axis='y', linestyle='--', alpha=0.4)

    plt.tight_layout()
    plt.savefig(os.path.join(GRAFICOS_DIR, "dns_vs_transferencia.png"), bbox_inches='tight', dpi=300)
    plt.close()

def plot_overhead(resumo):
    arquivos = sorted(resumo['Tamanho_Arquivo'].unique(), key=sort_key_tamanho)
    perdas = sorted(resumo['Perda'].unique())
    
    fig, axes = plt.subplots(1, len(arquivos), figsize=(6 * len(arquivos), 6), sharey=False)
    fig.suptitle('Overhead Estrutural e de Retransmissão (Bytes Adicionais)', fontsize=16, y=1.05)
    
    for i, arq in enumerate(arquivos):
        ax = axes[i] if len(arquivos) > 1 else axes
        df_arq = resumo[resumo['Tamanho_Arquivo'] == arq]
        
        tcp_over = df_arq[df_arq['Protocolo'] == 'tcp']['Overhead'].values
        rudp_over = df_arq[df_arq['Protocolo'] == 'rudp']['Overhead'].values
        
        x = np.arange(len(perdas))
        width = 0.35
        
        if len(tcp_over) < len(x): tcp_over = np.pad(tcp_over, (0, len(x) - len(tcp_over)))
        if len(rudp_over) < len(x): rudp_over = np.pad(rudp_over, (0, len(x) - len(rudp_over)))
        
        bars1 = ax.bar(x - width/2, tcp_over, width, label='TCP', color='#1f77b4') 
        bars2 = ax.bar(x + width/2, rudp_over, width, label='R-UDP', color='#ff7f0e') 
        
        ax.bar_label(bars1, fmt='%.0f', padding=3, fontsize=9)
        ax.bar_label(bars2, fmt='%.0f', padding=3, fontsize=9)
        
        # FIX: Legenda no topo e Y extendido
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=2, frameon=False, fontsize=9)
        ax.set_ylim(0, max(tcp_over.max(), rudp_over.max()) * 1.3)
        
        ax.set_title(f'Tamanho: {arq}')
        ax.set_xlabel('Perda de Pacotes (%)')
        ax.set_ylabel('Overhead (Bytes)')
        ax.set_xticks(x)
        ax.set_xticklabels([f"{p}%" for p in perdas])
        ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(GRAFICOS_DIR, "overhead.png"), bbox_inches='tight', dpi=300)
    plt.close()

def plot_throughput(resumo):
    arquivos = sorted(resumo['Tamanho_Arquivo'].unique(), key=sort_key_tamanho)
    perdas = sorted(resumo['Perda'].unique())
    
    fig, axes = plt.subplots(1, len(arquivos), figsize=(6 * len(arquivos), 6), sharey=False)
    fig.suptitle('Throughput da Aplicação (Mbps)', fontsize=16, y=1.05)
    
    for i, arq in enumerate(arquivos):
        ax = axes[i] if len(arquivos) > 1 else axes
        df_arq = resumo[resumo['Tamanho_Arquivo'] == arq]
        
        tcp_tp = df_arq[df_arq['Protocolo'] == 'tcp']['Throughput'].values
        rudp_tp = df_arq[df_arq['Protocolo'] == 'rudp']['Throughput'].values
        
        x = np.arange(len(perdas))
        width = 0.35
        
        if len(tcp_tp) < len(x): tcp_tp = np.pad(tcp_tp, (0, len(x) - len(tcp_tp)))
        if len(rudp_tp) < len(x): rudp_tp = np.pad(rudp_tp, (0, len(x) - len(rudp_tp)))
        
        bars1 = ax.bar(x - width/2, tcp_tp, width, label='TCP', color='#1f77b4') 
        bars2 = ax.bar(x + width/2, rudp_tp, width, label='R-UDP', color='#ff7f0e') 
        
        ax.bar_label(bars1, fmt='%.2f', padding=3, fontsize=9)
        ax.bar_label(bars2, fmt='%.2f', padding=3, fontsize=9)
        
        # FIX: Legenda no topo e Y extendido
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=2, frameon=False, fontsize=9)
        ax.set_ylim(0, max(tcp_tp.max(), rudp_tp.max()) * 1.3)
        
        ax.set_title(f'Tamanho: {arq}')
        ax.set_xlabel('Perda de Pacotes (%)')
        ax.set_ylabel('Throughput (Mbps)')
        ax.set_xticks(x)
        ax.set_xticklabels([f"{p}%" for p in perdas])
        ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(GRAFICOS_DIR, "throughput.png"), bbox_inches='tight', dpi=300)
    plt.close()

def extrair_sequencia_logica(pcap_file):
    cmd = [
        "tshark", "-r", pcap_file,
        "-Y", "udp.port == 53 or tcp.port == 8080 or udp.port == 8081",
        "-c", "25"
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return resultado.stdout

def extrair_estatisticas_tempo(pcap_file):
    cmd = [
        "tshark", "-r", pcap_file,
        "-q", "-z", "conv,tcp", "-z", "conv,udp"
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return resultado.stdout
    
def extrair_metricas_pcap(pcap_file):
    bytes_total = os.path.getsize(pcap_file)
    duracao = 0.0
    
    cmd = ["tshark", "-r", pcap_file, "-T", "fields", "-e", "frame.time_relative", "-E", "separator=,"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    linhas = [l for l in res.stdout.strip().split('\n') if l]
    if linhas: duracao = float(linhas[-1].strip())
        
    return float(bytes_total), duracao

def plot_app_vs_pcap(df_app, pcaps_dados):
    if not pcaps_dados or df_app is None: return
    
    df_pcap = pd.DataFrame(pcaps_dados)
    df_pcap = df_pcap.groupby(['Tamanho_Arquivo', 'Protocolo', 'Perda']).mean().reset_index()
    
    resumo_app = df_app.groupby(['Tamanho_Arquivo', 'Protocolo', 'Perda'])[['Bytes_Enviados', 'Bytes_Recebidos', 'Tempo_Total']].mean().reset_index()
    resumo_app['Bytes_App_Total'] = resumo_app['Bytes_Enviados'] + resumo_app['Bytes_Recebidos']
    
    arquivos = sorted(resumo_app['Tamanho_Arquivo'].unique(), key=sort_key_tamanho)
    
    for arq in arquivos:
        df_arq = resumo_app[resumo_app['Tamanho_Arquivo'] == arq]
        df_merge = pd.merge(df_arq, df_pcap, on=['Tamanho_Arquivo', 'Protocolo', 'Perda'], how='inner')
        
        if df_merge.empty: continue

        labels = [f"{r['Protocolo'].upper()}\n({r['Perda']}%)" for _, r in df_merge.iterrows()]
        x = np.arange(len(labels))
        width = 0.35

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle(f'Aplicação vs Rede Real (PCAP) - Tamanho: {arq}', fontsize=14)

        # Gráfico 1: Volume
        b1 = ax1.bar(x - width/2, df_merge['Bytes_App_Total'], width, label='Aplicação (CSV)', color='#1f77b4')
        b2 = ax1.bar(x + width/2, df_merge['Bytes_PCAP'], width, label='Rede (PCAP)', color='#ff7f0e')
        
        # Converte os valores brutos para labels
        labels_b1 = [formatar_bytes(v) for v in df_merge['Bytes_App_Total']]
        labels_b2 = [formatar_bytes(v) for v in df_merge['Bytes_PCAP']]
        
        # rotation=0 coloca na horizontal, fontsize=7 reduz o tamanho para caber
        ax1.bar_label(b1, labels=labels_b1, rotation=0, padding=3)
        ax1.bar_label(b2, labels=labels_b2, rotation=0, padding=3)
        
        ax1.set_title('Volume de Dados Trafegados')
        ax1.set_ylabel('Bytes')
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, rotation=0) # Também deixei o eixo X na horizontal
        ax1.margins(y=0.25) # Espaço extra para o label não bater no teto
        ax1.legend()

        # Gráfico 2: Tempo
        b3 = ax2.bar(x - width/2, df_merge['Tempo_Total'], width, label='Aplicação (CSV)', color='#1f77b4')
        b4 = ax2.bar(x + width/2, df_merge['Tempo_PCAP'], width, label='Rede (PCAP)', color='#ff7f0e')
        ax2.bar_label(b3, fmt='%.2f', fontsize=9)
        ax2.bar_label(b4, fmt='%.2f', fontsize=9)
        
        ax2.set_title('Duração (Segundos)')
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, rotation=45)
        ax2.margins(y=0.15)
        ax2.legend()

        plt.tight_layout()
        safe_name = arq.replace(" ", "").lower()
        plt.savefig(os.path.join(GRAFICOS_DIR, f"app_pcap_{safe_name}.png"), dpi=300)
        plt.close()
    
def processar_dossie_pcaps(df_app):
    arquivos_pcap = glob.glob(os.path.join(PCAP_DIR, "*.pcap"))
    pcaps_dados = []

    with open(DOSSIE_PATH, "w") as relatorio:
        relatorio.write("====================================================\n")
        relatorio.write("   DOSSIÊ AUTOMATIZADO DE COMPROVAÇÃO DE TRÁFEGO    \n")
        relatorio.write("====================================================\n\n")

        for pcap in arquivos_pcap:
            nome_arquivo = os.path.basename(pcap)
            nome_limpo = nome_arquivo.lower().replace(".pcap", "")
            partes = nome_limpo.split('_')
            
            proto = None
            perda = 0
            tam_formatado = "Desconhecido"
            
            for p in partes:
                if 'tcp' in p: 
                    proto = 'tcp'
                elif 'rudp' in p: 
                    proto = 'rudp'
                elif 'kb' in p or 'mb' in p: 
                    tam_formatado = p.replace('kb', ' KB').replace('mb', ' MB').upper()
                elif p.isdigit(): 
                    perda = int(p)

            if proto:
                bytes_pcap, tempo_pcap = extrair_metricas_pcap(pcap)
                pcaps_dados.append({
                    'Tamanho_Arquivo': tam_formatado,
                    'Protocolo': proto,
                    'Perda': perda,
                    'Bytes_PCAP': bytes_pcap,
                    'Tempo_PCAP': tempo_pcap
                })

            relatorio.write(f"### ANÁLISE DO CENÁRIO: {nome_arquivo} ###\n\n")
            relatorio.write("1. SEQUÊNCIA LÓGICA (DNS Custom -> Transporte -> Aplicação HTTP)\n")
            relatorio.write("-" * 60 + "\n")
            relatorio.write(extrair_sequencia_logica(pcap) + "\n")
            relatorio.write("2. CONFRONTO DE TEMPOS (Estatísticas de Conversação)\n")
            relatorio.write("-" * 60 + "\n")
            relatorio.write(extrair_estatisticas_tempo(pcap) + "\n")
            relatorio.write("=" * 60 + "\n\n")

    plot_app_vs_pcap(df_app, pcaps_dados)

def main():
    num_runs = ler_config_env()
    
    df = carregar_dados_e_inferir_contexto(num_runs)
    if df is not None:
        resumo_df = gerar_tabelas_resumo(df)
        
        plot_tempo_total(resumo_df)
        plot_dns_vs_http(resumo_df)
        plot_overhead(resumo_df)
        plot_throughput(resumo_df)
    
    processar_dossie_pcaps(df)

if __name__ == "__main__":
    main()