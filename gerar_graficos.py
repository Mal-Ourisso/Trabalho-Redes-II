import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from utils import DADOS_CONSOLIDADOS

# Extrai a quantidade de testes realizadas por cenário
# É assumido que a ordem foi: A -> B -> C
def carregar_num_runs(arquivo='config.env'):
    try:
        with open(arquivo, 'r') as f:
            for linha in f:
                if linha.strip().startswith('NUM_RUNS='):
                    return int(linha.split('=')[1].strip())
    except FileNotFoundError:
        print("[!] Aviso: 'config.env' não encontrado. Usando 15 por padrão.")
    return 15

def adicionar_rotulos(ax, barras):
    """Adiciona o valor no topo de cada barra."""
    for barra in barras:
        altura = barra.get_height()
        ax.annotate(f'{altura:.2f}', # Formato: 2 casas decimais
                    xy=(barra.get_x() + barra.get_width() / 2, altura),
                    xytext=(0, 3),  # Deslocamento vertical de 3 pontos
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)
        
try:
    df_app = pd.read_csv(DADOS_CONSOLIDADOS)
except FileNotFoundError:
    print(f"[!] Erro: O ficheiro '{DADOS_CONSOLIDADOS}' não foi encontrado.")
    exit()

# Adiciona a coluna de Cenários
num_runs = carregar_num_runs()
cenarios_lista = (
    ['A (0% Perda)'] * num_runs * 2 + 
    ['B (5% Perda)'] * num_runs * 2 + 
    ['C (10% Perda)'] * num_runs * 2
)

if len(df_app) == (num_runs * 6):
    df_app['Cenario'] = cenarios_lista
else:
    df_app['Cenario'] = ['Desconhecido'] * len(df_app)

# =====================================================================
# TABELA DE ESTATÍSTICAS (Mín, Média, Máx, Desvio)
# =====================================================================
estatisticas = df_app.groupby(['Cenario', 'Protocolo'])['Throughput_Mbps'].agg(
    Minimo='min', Media='mean', Maximo='max', Desvio_Padrao='std'
).reset_index()

metricas_file = 'metricas.csv'
estatisticas.to_csv(metricas_file, index=False)
print(f"[*] Tabela de estatísticas gerada: '{metricas_file}'")

# =====================================================================
# GRÁFICO DE THROUGHPUT COMPARATIVO
# =====================================================================
cenarios_labels = ['Cenário A', 'Cenário B', 'Cenário C']
media_tcp = estatisticas[estatisticas['Protocolo'] == 'TCP']['Media'].to_numpy(dtype=float)
media_rudp = estatisticas[estatisticas['Protocolo'] == 'R-UDP']['Media'].to_numpy(dtype=float)

x = np.arange(len(cenarios_labels))
largura_barra = 0.35

fig, ax = plt.subplots(figsize=(10, 6))
barras_tcp = ax.bar(x - largura_barra/2, media_tcp, largura_barra, label='TCP', color='#1f77b4', alpha=0.9)
barras_rudp = ax.bar(x + largura_barra/2, media_rudp, largura_barra, label='R-UDP', color='#ff7f0e', alpha=0.9)
adicionar_rotulos(ax, barras_tcp)
adicionar_rotulos(ax, barras_rudp)

ax.set_ylabel('Throughput Médio (Mbps)', fontsize=12)
ax.set_title('Throughput Médio em Escala Log (TCP vs R-UDP)', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(cenarios_labels)
ax.legend()
ax.set_yscale('log')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

throughtput_file = 'throughput.png'
plt.savefig(throughtput_file, dpi=300)
print(f"[*] Gráfico de throughput gerado: '{throughtput_file}'")

# =====================================================================
# VALIDAÇÃO CRUZADA COM O WIRESHARK
# =====================================================================
resultados_cruzados = []
cenarios_nom = ['A', 'B', 'C']
protocolos_nom = ['TCP', 'RUDP']

for cen in cenarios_nom:
    for prot in protocolos_nom:
        arquivo_ws = f"captura_{cen}_{prot}.csv"
        
        if os.path.exists(arquivo_ws):
            df_ws = pd.read_csv(arquivo_ws)
            col_len = 'Length' if 'Length' in df_ws.columns else 'frame.len'
            col_time = 'Time' if 'Time' in df_ws.columns else 'frame.time_relative'

            # Métricas da Rede (Wireshark)
            vol_rede_kb = df_ws[col_len].sum() / 1024 # Convertido para KB
            tempo_rede_segs = df_ws[col_time].max() - ((num_runs - 1) * 0.5) # Subtrai os 'sleeps' do bash
            
            # Métricas da Aplicação (Python)
            prot_app = 'TCP' if prot == 'TCP' else 'R-UDP'
            filtro_app = df_app[(df_app['Cenario'].str.startswith(cen)) & (df_app['Protocolo'] == prot_app)]
            
            vol_app_kb = filtro_app['Volume_Bytes'].sum() / 1024 # Convertido para KB
            tempo_app_somado = filtro_app['Tempo_Segundos'].sum()

            resultados_cruzados.append({
                'Cenario_Prot': f"{cen}-{prot}",
                'Vol_App_KB': vol_app_kb,
                'Vol_Rede_KB': vol_rede_kb,
                'Tempo_App_S': tempo_app_somado,
                'Tempo_Rede_S': tempo_rede_segs
            })

# =====================================================================
# GRÁFICOS DA VALIDAÇÃO CRUZADA
# =====================================================================
if resultados_cruzados:
    df_cruz = pd.DataFrame(resultados_cruzados)
    labels_cruz = df_cruz['Cenario_Prot'].tolist()
    x_cruz = np.arange(len(labels_cruz))
    
    # --- VALIDAÇÃO DE VOLUME ---
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    barras_app_vol = ax2.bar(x_cruz - largura_barra/2, df_cruz['Vol_App_KB'], largura_barra, label='App (Payload)', color='#1f77b4', alpha=0.9)
    barras_ws_vol = ax2.bar(x_cruz + largura_barra/2, df_cruz['Vol_Rede_KB'], largura_barra, label='Rede (Wireshark)', color='#ff7f0e', alpha=0.9)
    adicionar_rotulos(ax2, barras_app_vol)
    adicionar_rotulos(ax2, barras_ws_vol)
    
    ax2.set_ylabel('Volume Total (KB)', fontsize=12)
    ax2.set_title('Validação Cruzada: Volume de Dados', fontsize=14, fontweight='bold')
    ax2.set_xticks(x_cruz)
    ax2.set_xticklabels(labels_cruz)
    ax2.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    valid_vol_file = 'validacao_volume.png'
    plt.savefig(valid_vol_file, dpi=300)
    print(f"[*] Gráfico de Validação de Volume gerado: '{valid_vol_file}'")

    # --- VALIDAÇÃO DE TEMPO ---
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    barras_app_time = ax3.bar(x_cruz - largura_barra/2, df_cruz['Tempo_App_S'], largura_barra, label='App (Python)', color='#1f77b4', alpha=0.9)
    barras_ws_time = ax3.bar(x_cruz + largura_barra/2, df_cruz['Tempo_Rede_S'], largura_barra, label='Rede (Wireshark)', color='#ff7f0e', alpha=0.9)
    adicionar_rotulos(ax3, barras_app_time)
    adicionar_rotulos(ax3, barras_ws_time)

    ax3.set_ylabel('Tempo Total (Segundos)', fontsize=12)
    ax3.set_title('Validação Cruzada: Tempo de Execução em Escala Log', fontsize=14, fontweight='bold')
    ax3.set_xticks(x_cruz)
    ax3.set_xticklabels(labels_cruz)
    ax3.legend()
    ax3.set_yscale('log')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    valid_time_file = 'validacao_tempo.png'
    plt.savefig(valid_time_file, dpi=300)
    print(f"[*] Gráfico de Validação de Tempo gerado: '{valid_time_file}'")
else:
    print("[!] Gráficos de validação ignorados (ficheiros CSV do Wireshark não encontrados).")