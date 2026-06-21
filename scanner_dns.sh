#!/bin/bash
# scanner_dns.sh - Scans Linkfort network for active DNS servers

NETWORK="138.97.220"
DOMAIN="google.com"
TIMEOUT=1

echo "🔍 Scanner Linkfort DNS v1.0"
echo "Buscando servidores ativos no range $NETWORK.1-254..."
echo "--------------------------------------------------------"

# Armazenar resultados em um temporário
TEMP_FILE="/tmp/dns_ativos.txt"
> "$TEMP_FILE"

for i in {1..254}; do
    ip="$NETWORK.$i"
    # Executa dig em subshell background para velocidade
    (
        if dig "@$ip" "$DOMAIN" +short +timeout=$TIMEOUT +tries=1 2>/dev/null | grep -q '^[0-9]'; then
            echo "$ip" >> "$TEMP_FILE"
            echo "  [+] Ativo: $ip"
        fi
    ) &
    
    # Controle de paralelismo (blocos de 64 pids)
    if (( i % 64 == 0 )); then wait; fi
done

wait
echo "--------------------------------------------------------"
echo "Relatório Final: $(wc -l < "$TEMP_FILE") servidores encontrados."
echo "Lista salva em $TEMP_FILE"
