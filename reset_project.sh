#!/bin/bash
echo "[*] Limpando diretórios..."

for dir in temp_files results capturas; do
    if [ -d "$dir" ]; then
        rm -rf "$dir"/*
        echo "[+] $dir limpo."
    fi
done

echo "[+] Limpeza concluída."