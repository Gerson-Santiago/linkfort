# 🛡️ Linkfort DNS Monitor v3.0

O **Linkfort DNS Monitor** é uma plataforma premium de análise de performance de rede, focada em medir a latência e estabilidade de servidores DNS globais e locais em tempo real.

## 🌟 O que há de novo (Source of Truth)

Diferente de monitores simples, o Linkfort agora oferece uma experiência de "DASHBOARD VIVO":

- **🌊 Seamless Updates (Zero F5):** O dashboard se atualiza sozinho a cada 15 segundos sem "piscar" a tela.
- **📈 Métricas Estáveis (Jitter & P95):** Além da média, o sistema agora reporta a variação (Jitter) e os picos de latência (P95), permitindo identificar redes instáveis na hora.
- **⏱️ Countdown Timer:** Um cronômetro no cabeçalho indica exatamente quando a próxima rodada de testes será exibida.
- **📝 Exportação .TXT:** Um botão dedicado para baixar o ranking atual organizado em um arquivo de texto formatado.
- **🛑 Controle Total:** Botão "STOP SYSTEM" na interface que encerra o servidor e o monitor bash simultaneamente.
- **🆔 Monitoramento Transparente:** Exibição do PID real e da rodada atual diretamente no cabeçalho.

---

## 🏗️ Arquitetura do Sistema

1. **Coletor (`monitor_dados.sh`):** Motor em Bash que realiza testes `dig` em paralelo, salvando o histórico em `dados_dns_linkfort.csv`.
2. **Orquestrador (`server.js`):** Servidor Node.js que gerencia o processo de monitoramento e serve a API do dashboard.
3. **Engine Visual (`gerar_dashboard.py`):** Script Python que processa o CSV e gera o HTML ultra-moderno com *Chart.js* e *Glassmorphism*.

---

## 🚀 Como Iniciar (O Jeito Fácil)

Agora você tem um atalho global no seu terminal. Não importa onde você esteja:

1. **Abra o terminal e digite:**
   ```bash
   linkfort
   ```
   *Este comando limpa instâncias antigas automaticamente e inicia o sistema fresh.*

2. **Acesse a interface:**
   [http://localhost:3000](http://localhost:3000)

---

## 📦 Requisitos do Sistema

- **dnsutils (`dig`):** Para as coletas de rede.
- **Python 3:** Para a lógica de processamento de dados.
- **Node.js:** Para o servidor de interface e orquestração.

---

## 🛠️ Comandos Úteis

- **Parada Forçada:** `pkill -9 -f "node server.js"`
- **Limpeza de Logs:** `rm dados_dns_linkfort.csv` (O sistema criará um novo na próxima rodada).

---
*Linkfort: Inteligência em DNS com Estética de Próxima Geração.*
