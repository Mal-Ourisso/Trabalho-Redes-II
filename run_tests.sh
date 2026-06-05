#!/bin/bash

# Carrega o número de testes a ser realizado por cenário
source config.env

INTERFACE="eth0" 

echo "[*] Limpando arquivos de execuções anteriores..."
rm -f *.txt 
rm -f *.pcap 
rm -f *.csv 
rm -f *.png 
echo ""

tc qdisc del dev $INTERFACE root 2>/dev/null

run_scenario() {
    SCENARIO_NAME=$1
    PROTOCOL=$2
    DELAY=$3
    LOSS=$4

    echo "====================================================="
    echo " Cenário $SCENARIO_NAME | Protocolo: $PROTOCOL "
    echo "====================================================="

    # Configurando Rede no Cliente
    if [ "$LOSS" == "0%" ]; then
        tc qdisc add dev $INTERFACE root netem delay $DELAY
    else
        tc qdisc add dev $INTERFACE root netem delay $DELAY loss $LOSS
    fi

    # Iniciando TCPDump com Filtro de Porta
    PCAP_FILE="captura_${SCENARIO_NAME}_${PROTOCOL}.pcap"
    
    if [ "$PROTOCOL" == "TCP" ]; then
        # Captura apenas tráfego TCP na porta 5000
        tcpdump -i $INTERFACE tcp port 5000 -w $PCAP_FILE 2>/dev/null &
    else
        # Captura apenas tráfego UDP na porta 5001
        tcpdump -i $INTERFACE udp port 5001 -w $PCAP_FILE 2>/dev/null &
    fi
    
    TCPDUMP_PID=$!
    sleep 1

    # Executando o Cliente
    LOG_FILE="resultados_${SCENARIO_NAME}_${PROTOCOL}.txt"
    echo "Executando transferências para o servidor..."
    
    for i in $(seq 1 $NUM_RUNS); do
        if [ "$PROTOCOL" == "TCP" ]; then
            python3 client.py --protocol tcp >> $LOG_FILE
        else
            python3 client.py --protocol rudp >> $LOG_FILE
        fi
        echo " -> Transferência $i concluída"
        sleep 0.5
    done

    # Encerra Captura e Limpa Rede
    kill -2 $TCPDUMP_PID 
    wait $TCPDUMP_PID 2>/dev/null
    tc qdisc del dev $INTERFACE root
    echo "Cenário $SCENARIO_NAME ($PROTOCOL) concluído!"
    echo ""
}

run_scenario "A" "TCP" "10ms" "0%"
run_scenario "A" "RUDP" "10ms" "0%"

run_scenario "B" "TCP" "50ms" "5%"
run_scenario "B" "RUDP" "50ms" "5%"

run_scenario "C" "TCP" "100ms" "10%"
run_scenario "C" "RUDP" "100ms" "10%"

# Deletando arquivos de teste gerados por client.py
rm -f recebido_*.dat
rm -f teste_envio.txt