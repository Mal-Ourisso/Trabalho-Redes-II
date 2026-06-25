#!/bin/bash
source config.env
IF="eth0"
TEMP="temp_files"
RES="results"
CAP="capturas"

# Prepara ambiente
bash ./reset_project.sh
mkdir -p $TEMP $RES $CAP

# Gera arquivos de teste
for s in 5 10 50; do
    dd if=/dev/urandom of="$TEMP/${s}kb.dat" bs=1024 count=$s status=none
done

run_scenario() {
    NAME=$1
    PROTO=$2
    DELAY=$3
    LOSS=$4
    echo "Executando: $NAME | $PROTO | Perda: $LOSS"

    # Configura traffic control
    tc qdisc add dev $IF root netem delay $DELAY loss $LOSS 2>/dev/null
    
    for s in 5 10 50; do
        pcap="$CAP/cap_${NAME}_${PROTO}_${s}kb.pcap"
        tcpdump -i $IF -n -s 0 port 5053 or port 8080 or port 8081 -w "$pcap" 2>/dev/null &
        pid=$!
        
        for i in $(seq 1 $NUM_RUNS); do
            python3 client.py --protocol "$PROTO" --file "$TEMP/${s}kb.dat" >> "$TEMP/exec_${NAME}_${PROTO}.txt"
        done
        kill $pid && wait $pid 2>/dev/null
    done
    tc qdisc del dev $IF root 2>/dev/null
}

# Cenários
run_scenario "A" "TCP" "10ms" "0%"
run_scenario "A" "RUDP" "10ms" "0%"
run_scenario "B" "TCP" "50ms" "5%"
run_scenario "B" "RUDP" "50ms" "5%"
run_scenario "C" "TCP" "100ms" "10%"
run_scenario "C" "RUDP" "100ms" "10%"