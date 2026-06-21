#!/bin/bash
# monitor_dados.sh
# Coletor de métricas DNS para o Projeto Linkfort v3.4
# Arquitetura: Coleta (Bash) -> CSV -> Análise (Python)

BASE_DIR=$(dirname "$(readlink -f "$0")")
OUTPUT_FILE="$BASE_DIR/dados_dns_linkfort.csv"
DOMAINS=(
    # --- Gerais ---
    "google.com"
    "amazon.com"
    "youtube.com"
    "netflix.com"
    "chatgpt.com"
    "gemini.google.com"
    "canva.com"
    "uol.com.br"
    "sei.univesp.br"
    "bertioga.sp.gov.br"

    # --- Riot / Valorant (validados ✅) ---
    "valorant.com"
    "playvalorant.com"
    "auth.riotgames.com"
    "entitlements.auth.riotgames.com"
    "clientconfig.rpg.riotgames.com"
    "br.api.riotgames.com"
    "valorant-api.com"
)


# Mapa de DNS (Array associativo requer Bash 4+)
declare -A DNS_MAP

# Ordem de execução (Apenas Servidores Ativos)
DNS_IPS=(
    "138.97.220.58"  # Linkfort_1
    "138.97.220.62"  # Linkfort_2
    "138.97.220.242" # Linkfort_3 (Descoberto)
    "138.97.220.243" # Linkfort_4 (Descoberto)
    "8.8.8.8"        # Google_Pri
    "8.8.4.4"        # Google_Sec
    "1.1.1.1"        # Cloudflare_Pri
    "1.0.0.1"        # Cloudflare_Sec
)

DNS_MAP["138.97.220.58"]="Linkfort_1"
DNS_MAP["138.97.220.62"]="Linkfort_2"
DNS_MAP["138.97.220.242"]="Linkfort_3"
DNS_MAP["138.97.220.243"]="Linkfort_4"
DNS_MAP["8.8.8.8"]="Google_Pri"
DNS_MAP["8.8.4.4"]="Google_Sec"
DNS_MAP["1.1.1.1"]="Cloudflare_Pri"
DNS_MAP["1.0.0.1"]="Cloudflare_Sec"

# Função para criar links clicáveis no terminal (OSC 8)
link() {
    local url=$1
    local text=$2
    printf "\e]8;;%s\a%s\e]8;;\a" "$url" "$text"
}

# Inicializa CSV se não existir
if [ ! -f "$OUTPUT_FILE" ]; then
    echo "timestamp,dns_name,dns_ip,domain,latency_ms,status" > "$OUTPUT_FILE"
fi

# Função de help
if [[ "$1" == "--help" ]]; then
    echo "Uso: $0 [--count N]"
    echo "  --count N : Executa N rodadas de testes e para (padrão: loop infinito)"
    exit 0
fi

# Configuração de repetição e silêncio
COUNT=-1
SILENT=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --count) COUNT="$2"; shift ;;
        --silent) SILENT=true ;;
        --help) 
            echo "Uso: $0 [--count N] [--silent]"
            echo "  --count N : Executa N rodadas de testes e para"
            echo "  --silent  : Omite os pontos (.) de feedback no terminal"
            exit 0
            ;;
    esac
    shift
done

# Limpeza ao sair
cleanup() {
    echo "STOPPED" > "$BASE_DIR/.monitor_status"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "--- Iniciando Coletor Linkfort v3.4 ---"
echo -e "Saída: $(link "file://$OUTPUT_FILE" "$OUTPUT_FILE")"
echo -e "Dashboard: $(link "http://localhost:3000" "http://localhost:3000")"
echo "DNSs: ${DNS_IPS[@]}"
echo "Domains: ${DOMAINS[@]}"
echo "---------------------------------------"

RODADA=0
while [[ $COUNT -ne 0 ]]; do
    ((RODADA++))
    echo "RUNNING:$RODADA:$$" > "$BASE_DIR/.monitor_status"
    
    CURRENT_TIME=$(date '+%H:%M:%S') # Define CURRENT_TIME for this iteration
    echo "[$CURRENT_TIME] Rodada $RODADA..."

    for ip in "${DNS_IPS[@]}"; do
        name="${DNS_MAP[$ip]}"
        
        for domain in "${DOMAINS[@]}"; do
            timestamp=$(date '+%Y-%m-%d %H:%M:%S')
            
            # Executa dig
            # Captura stats completos para extrair STATUS e QUERY TIME
            output=$(dig "@$ip" "$domain" +stats +tries=2 +timeout=2 2>&1)
            
            # Extrai tempo (Query time: N msec)
            latency=$(echo "$output" | grep "Query time:" | awk '{print $4}')
            
            # Extrai status (status: NOERROR, status: REFUSED, etc)
            dig_status=$(echo "$output" | grep "status:" | awk '{print $6}' | sed 's/,//')

            # Normalização de Status e Latência
            if [[ -z "$latency" ]]; then
                latency="0"
                status="TIMEOUT"
            else
                if [[ "$dig_status" == "NOERROR" ]]; then
                    status="OK"
                    # Se latência for 0, registramos como 1 para indicar 'sub-1ms' (cache hit)
                    if [[ "$latency" -eq 0 ]]; then
                        latency="1"
                    fi
                else
                    status="$dig_status"
                fi
            fi
            
            # Escreve no CSV
            echo "$timestamp,$name,$ip,$domain,$latency,$status" >> "$OUTPUT_FILE"
            
            # Sleep moderado para não saturar buffer (Subhost mitigation)
            sleep 0.5
            
    # Feedback visual (apenas se não for silencioso)
    if [[ "$SILENT" != "true" ]]; then
        echo -n "."
    fi
done
done
if [[ "$SILENT" != "true" ]]; then
    echo "" # Quebra linha após os pontos
fi
    
    echo "   -> Rodada concluída. Atualizando Dashboard..."
    
    # V3.5: Auto-Update do Dashboard (DRY)
    # Usa variável exportada pelo linkfort ou fallback
    PYTHON_CMD="${PYTHON_EXEC:-python3}"
    
    # Se não foi exportado e existe venv, usa (fallback legacy)
    if [ -z "$PYTHON_EXEC" ] && [ -f "$BASE_DIR/.venv/bin/python3" ]; then
        PYTHON_CMD="$BASE_DIR/.venv/bin/python3"
    fi

    "$PYTHON_CMD" "$BASE_DIR/gerar_dashboard.py"

    # Decrementa contador se não for infinito (-1)
    if [[ $COUNT -gt 0 ]]; then
        ((COUNT--))
    fi
done

echo "Coleta finalizada ($RODADA rodadas)."
