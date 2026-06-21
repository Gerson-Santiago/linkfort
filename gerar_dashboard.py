#!/usr/bin/env python3
import csv
import os
from datetime import datetime
import json
import statistics

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "dados_dns_linkfort.csv")
HTML_FILE = os.path.join(BASE_DIR, "dashboard.html")

def generate_dashboard():
    if not os.path.exists(CSV_FILE):
        return

    dns_data = {}
    timestamps = []

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dns_name = row['dns_name']
            latency = float(row['latency_ms'])
            status = row['status']
            ts = row['timestamp']
            
            if dns_name not in dns_data:
                dns_data[dns_name] = {
                    'ip': row['dns_ip'],
                    'total_requests': 0,
                    'successful': 0,
                    'total_latency': 0,
                    'timeouts': 0,
                    'errors': 0,
                    'history': []
                }
            
            dns_data[dns_name]['total_requests'] += 1
            if status == "OK":
                dns_data[dns_name]['successful'] += 1
                dns_data[dns_name]['total_latency'] += latency
                dns_data[dns_name]['history'].append({'ts': ts, 'lat': latency})
            elif status == "TIMEOUT":
                dns_data[dns_name]['timeouts'] += 1
            else:
                dns_data[dns_name]['errors'] += 1
                
    labels = []
    latencies = []
    success_rates = []
    bg_colors = []
    
    # Sort order: Linkfort first, then others
    sorted_dns = sorted(dns_data.keys(), key=lambda x: (not x.startswith('Linkfort'), x))
    
    for dns in sorted_dns:
        stats = dns_data[dns]
        labels.append(dns)
        
        avg_lat = stats['total_latency'] / stats['successful'] if stats['successful'] > 0 else 0
        latencies.append(round(avg_lat, 2))
        
        rate = (stats['successful'] / stats['total_requests']) * 100 if stats['total_requests'] > 0 else 0
        success_rates.append(round(rate, 2))
        
        if "Linkfort" in dns:
            bg_colors.append("rgba(54, 162, 235, 0.8)") # Blue
        elif "Google" in dns:
            bg_colors.append("rgba(255, 206, 86, 0.8)") # Yellow
        elif "Cloudflare" in dns:
            bg_colors.append("rgba(255, 159, 64, 0.8)") # Orange
        else:
            bg_colors.append("rgba(153, 102, 255, 0.8)")

    # Global Ranking Logic (All DNS) for Recommendation and Table
    global_ranking = []
    for name, stats in dns_data.items():
        success_rate = (stats['successful'] / stats['total_requests']) if stats['total_requests'] > 0 else 0
        lats = [h['lat'] for h in stats['history']]
        avg_lat = statistics.mean(lats) if lats else 999
        
        # Jitter and P95
        jitter = statistics.stdev(lats) if len(lats) > 1 else 0.0
        p95 = sorted(lats)[int(0.95 * len(lats))] if lats else 999
        
        global_ranking.append({
            'name': name,
            'ip': stats['ip'],
            'success_rate': success_rate * 100,
            'avg_latency': avg_lat,
            'jitter': jitter,
            'p95': p95,
            'status': "OK" if stats['successful'] > 0 and stats['total_latency'] > 0 else "OFFLINE"
        })
    
    # Sort: Success Rate DESC, Latency ASC
    global_ranking.sort(key=lambda x: (-x['success_rate'], x['avg_latency']))
    
    top_dns = []
    if len(global_ranking) > 0:
        top_dns.append(global_ranking[0])
    if len(global_ranking) > 1:
        top_dns.append(global_ranking[1])
    
    recommendation_html = ""
    if len(top_dns) >= 2:
        recommendation_html = f"""
        <div class="card" style="background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(129, 140, 248, 0.2)); border: 1px solid var(--accent);">
            <h2 style="border-bottom: 1px solid var(--accent);">🏆 Recomendação para o Roteador</h2>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Configure estes IPs no seu roteador para obter a melhor performance baseada nos testes atuais:</p>
            <div class="mini-stats">
                <div class="stat-box" style="border: 1px solid var(--accent);">
                    <div class="stat-value" style="font-size: 1.5rem;">{top_dns[0]['ip']}</div>
                    <div class="stat-label">DNS Primário ({top_dns[0]['name']})</div>
                </div>
                <div class="stat-box" style="border: 1px solid var(--accent);">
                    <div class="stat-value" style="font-size: 1.5rem;">{top_dns[1]['ip']}</div>
                    <div class="stat-label">DNS Secundário ({top_dns[1]['name']})</div>
                </div>
                <div class="stat-box" style="display: flex; align-items: center; justify-content: center; background: rgba(56, 189, 248, 0.1);">
                    <div style="text-align: left;">
                        <div style="color: #4ade80; font-weight: 800; font-size: 1.2rem;">✓ Otimizado</div>
                        <div style="font-size: 0.7rem; color: var(--text-muted);">Baseado em latência real</div>
                    </div>
                </div>
            </div>
        </div>
        """
    else:
        recommendation_html = "<p>Aguardando mais dados para recomendação...</p>"

    # Read Monitor Status
    status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".monitor_status")
    monitor_status = "OFFLINE"
    monitor_round = "0"
    monitor_pid = "---"
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r') as f:
                content = f.read().strip().split(':')
                monitor_status = content[0]
                if len(content) > 1:
                    monitor_round = content[1]
                if len(content) > 2:
                    monitor_pid = content[2]
        except:
            pass

    table_rows_html = ""
    for i, item in enumerate(global_ranking):
        status_class = "status-ok" if item['status'] == "OK" else "status-err"
        table_rows_html += f"""
        <tr>
            <td><span class="rank-badge">{i+1}</span></td>
            <td style="font-weight: 600;">{item['name']}</td>
            <td style="color: var(--text-muted); font-family: monospace;">{item['ip']}</td>
            <td>{item['avg_latency']:.2f}ms</td>
            <td style="color: #a855f7;">{item['jitter']:.2f}ms</td>
            <td style="color: #f43f5e;">{item['p95']:.2f}ms</td>
            <td>{item['success_rate']:.1f}%</td>
            <td><span class="status-pill {status_class}">{item['status']}</span></td>
        </tr>
        """

    # Generate Text Report for Export
    report_file = os.path.join(BASE_DIR, "linkfort_report.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("==========================================\n")
        f.write("       RELATÓRIO DE PERFORMANCE DNS       \n")
        f.write("==========================================\n")
        f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write(f"Monitor: {monitor_status} (Rodada #{monitor_round})\n")
        f.write("------------------------------------------\n\n")
        f.write(f"{'RANK':<5} {'SERVIDOR':<20} {'IP':<16} {'AVG LAT':<10} {'JITTER':<10} {'P95':<10} {'SUCESSO':<10}\n")
        f.write("-" * 95 + "\n")
        for i, item in enumerate(global_ranking):
            f.write(f"{i+1:<5} {item['name']:<20} {item['ip']:<16} {item['avg_latency']:>7.2f}ms {item['jitter']:>7.2f}ms {item['p95']:>7.2f}ms {item['success_rate']:>8.1f}%\n")
        f.write("\n==========================================\n")
        f.write("Gerado automaticamente por Linkfort System\n")

    total_req = sum(stats['total_requests'] for stats in dns_data.values())
    total_succ = sum(stats['successful'] for stats in dns_data.values())
    total_err = sum(stats['errors'] + stats['timeouts'] for stats in dns_data.values())

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Linkfort DNS Monitoring</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: hsl(222, 47%, 7%);
            --card-bg: hsla(222, 47%, 12%, 0.7);
            --text-main: hsl(210, 40%, 98%);
            --text-muted: hsl(215, 20%, 65%);
            --accent: hsl(199, 89%, 48%);
            --accent-glow: hsla(199, 89%, 48%, 0.5);
            --success: hsl(142, 71%, 45%);
            --warning: hsl(48, 96%, 53%);
            --danger: hsl(0, 84%, 60%);
            --glass-border: hsla(0, 0%, 100%, 0.1);
        }}
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 2rem;
            min-height: 100vh;
            background-image: 
                radial-gradient(circle at 10% 20%, hsla(199, 89%, 48%, 0.1) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, hsla(263, 70%, 50%, 0.1) 0%, transparent 40%);
            background-attachment: fixed;
        }}
        .header {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        .header h1 {{
            font-size: 3rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(to right, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 30px var(--accent-glow);
        }}
        .header p {{
            color: var(--text-muted);
            font-size: 1.1rem;
            margin-top: 0.5rem;
        }}
        .last-update {{
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-top: 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 1.5rem;
        }}
        .refresh-countdown {{
            background: rgba(255, 255, 255, 0.05);
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.7rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }}
        .btn-export {{
            background: var(--accent);
            color: var(--bg-color);
            border: none;
            padding: 0.1rem 0.6rem;
            border-radius: 4px;
            font-size: 0.65rem;
            font-weight: 800;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
        }}
        .btn-export:hover {{
            background: #fff;
            transform: scale(1.05);
        }}
        /* Skeleton Screen Effect */
        .skeleton {{
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
        }}
        @keyframes shimmer {{
            0% {{ background-position: -200% 0; }}
            100% {{ background-position: 200% 0; }}
        }}
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 2rem;
            max-width: 1400px;
            margin: 0 auto;
            align-items: stretch;
        }}
        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-radius: 24px;
            padding: 2rem;
            border: 1px solid var(--glass-border);
            box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.5);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
        }}
        .card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 1px;
            background: linear-gradient(90deg, transparent, var(--glass-border), transparent);
        }}
        .card:hover {{
            transform: translateY(-8px) scale(1.01);
            box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.7);
            border-color: hsla(0, 0%, 100%, 0.2);
        }}
        h2 {{
            font-size: 1.25rem;
            font-weight: 600;
            margin-top: 0;
            margin-bottom: 1.5rem;
            color: #e2e8f0;
            border-bottom: 1px solid var(--glass-border);
            padding-bottom: 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .chart-container {{
            position: relative;
            height: 300px;
            width: 100%;
            flex-grow: 1;
        }}
        /* Table Styles */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}
        th {{
            text-align: left;
            padding: 1rem;
            color: var(--text-muted);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        td {{
            padding: 1rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 1rem;
        }}
        .rank-badge {{
            display: inline-block;
            width: 24px;
            height: 24px;
            line-height: 24px;
            text-align: center;
            border-radius: 50%;
            background: var(--accent);
            color: var(--bg-color);
            font-weight: 800;
            font-size: 0.8rem;
        }}
        .status-pill {{
            padding: 0.2rem 0.6rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .status-ok {{ background: rgba(74, 222, 128, 0.1); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.2); }}
        .status-err {{ background: rgba(248, 113, 113, 0.1); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.2); }}
        
        /* Alive Badge Animation */
        .live-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(34, 197, 94, 0.1);
            color: #4ade80;
            padding: 0.4rem 1rem;
            border-radius: 30px;
            font-size: 0.9rem;
            font-weight: 800;
            border: 1px solid rgba(34, 197, 94, 0.2);
            margin-top: 1rem;
        }}
        .dot {{
            width: 8px;
            height: 8px;
            background: #4ade80;
            border-radius: 50%;
            box-shadow: 0 0 10px #4ade80;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.7); }}
            70% {{ transform: scale(1); box-shadow: 0 0 0 10px rgba(74, 222, 128, 0); }}
            100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(74, 222, 128, 0); }}
        }}
        .round-info {{
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
            font-weight: 400;
        }}
        .pid-manager {{
            margin-top: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 1rem;
            background: rgba(15, 23, 42, 0.6);
            padding: 0.6rem 1.2rem;
            border-radius: 50px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            max-width: fit-content;
            margin-left: auto;
            margin-right: auto;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }}
        .pid-tag {{
            font-family: 'Outfit', sans-serif;
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent);
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.85rem;
        }}
        .pkill-cmd {{
            font-family: monospace;
            color: #f87171;
            cursor: pointer;
            padding: 0.4rem 0.8rem;
            background: rgba(248, 113, 113, 0.1);
            border: 1px solid rgba(248, 113, 113, 0.2);
            border-radius: 8px;
            font-size: 0.8rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .pkill-cmd:hover {{
            background: #f87171;
            color: white;
            transform: scale(1.02);
            box-shadow: 0 0 20px rgba(248, 113, 113, 0.4);
        }}
        .mini-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
            margin-top: auto;
        }}
        .stat-box {{
            background: rgba(15, 23, 42, 0.6);
            padding: 1rem;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .stat-value {{
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--accent);
        }}
        .stat-label {{
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 0.3rem;
        }}
        @media (max-width: 768px) {{
            .dashboard-grid {{
                grid-template-columns: 1fr;
            }}
            .header h1 {{
                font-size: 2.2rem;
            }}
        }}
    </style>
</head>
<body>
        <header class="header">
        <h1>Linkfort DNS Telemetry</h1>
        <p>Real-time performance metrics</p>
        
        {f'<div class="live-indicator"><div class="dot"></div> LIVE MONITOR</div><div class="round-info">Executando Rodada #{monitor_round}</div>' if monitor_status == "RUNNING" else '<div class="round-info" style="color: #f87171;">● MONITOR OFFLINE</div>'}

        <div class="pid-manager">
            <span style="font-size: 0.8rem; color: var(--text-muted); font-weight: 600;">MONITOR:</span>
            <span class="pid-tag">PID {monitor_pid}</span>
            <div class="pkill-cmd" onclick="stopSystem()" title="Desliga todo o sistema (Server + Monitor)">
                <span>STOP SYSTEM</span>
            </div>
        </div>

        <div class="last-update">
            <span id="update-ts">Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</span>
            <div class="refresh-countdown">
                <span id="countdown-box">Próxima em 15s</span>
                <button class="btn-export" onclick="exportData()">Exportar .TXT</button>
            </div>
        </div>
    </header>

    <div class="dashboard-grid">
        <div style="grid-column: 1 / -1;">
            {recommendation_html}
        </div>
        <div class="card">
            <h2>Average Latency (ms)</h2>
            <div class="chart-container">
                <canvas id="latencyChart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h2>Success Rate (%)</h2>
            <div class="chart-container">
                <canvas id="successChart"></canvas>
            </div>
        </div>
    </div>
    
    <div style="max-width: 1400px; margin: 2rem auto;">
        <div class="card" style="padding: 2rem;">
            <h2>📊 DNS Performance Ranking</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Servidor</th>
                        <th>IP Address</th>
                        <th>Latência (Média)</th>
                        <th style="color: #a855f7;">Jitter (StDev)</th>
                        <th style="color: #f43f5e;">P95 (Peak)</th>
                        <th>Sucesso</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
        </div>
    </div>

    <div style="max-width: 1400px; margin: 2rem auto;">
        <div class="card" style="padding: 2rem;">
            <h2>System Overview</h2>
            <div class="mini-stats">
                <div class="stat-box">
                    <div class="stat-value">{total_req}</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" style="color: #4ade80;">{total_succ}</div>
                    <div class="stat-label">Successful</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" style="color: #f87171;">{total_err}</div>
                    <div class="stat-label">Errors / Timeouts</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = "'Outfit', sans-serif";
        
        function stopSystem() {{
            if (confirm('Deseja realmente desligar todo o sistema Linkfort?')) {{
                fetch('/stop').then(() => {{
                    const el = document.querySelector('.pkill-cmd span');
                    el.innerText = 'DESLIGANDO... 🛑';
                    setTimeout(() => {{ 
                        document.body.innerHTML = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;color:#f87171;font-family:Outfit"><h1>Sistema Desligado</h1><p>O monitor e o servidor foram encerrados com sucesso.</p></div>';
                    }}, 2000);
                }});
            }}
        }}

        function exportData() {{
            window.location.href = '/export';
        }}

        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                const el = document.querySelector('.pkill-cmd span');
                const originalText = el.innerText;
                el.innerText = 'COPIADO! ✅';
                setTimeout(() => {{ el.innerText = originalText; }}, 2000);
            }});
        }}
        
        const labels = {json.dumps(labels)};
        const latencies = {json.dumps(latencies)};
        const bgColors = {json.dumps(bg_colors)};
        const successRates = {json.dumps(success_rates)};

        // Latency Chart
        const ctxLat = document.getElementById('latencyChart').getContext('2d');
        new Chart(ctxLat, {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Avg Latency (ms)',
                    data: latencies,
                    backgroundColor: bgColors,
                    borderWidth: 0,
                    borderRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}
                    }},
                    x: {{
                        grid: {{ display: false }}
                    }}
                }},
                animation: {{ duration: 0 }}
            }}
        }});
        
        // Success Rate Chart
        const ctxSucc = document.getElementById('successChart').getContext('2d');
        new Chart(ctxSucc, {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Success Rate (%)',
                    data: successRates,
                    backgroundColor: successRates.map(r => r > 95 ? 'rgba(74, 222, 128, 0.8)' : (r > 80 ? 'rgba(250, 204, 21, 0.8)' : 'rgba(248, 113, 113, 0.8)')),
                    borderWidth: 0,
                    borderRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}
                    }},
                    x: {{
                        grid: {{ display: false }}
                    }}
                }},
                animation: {{ duration: 0 }}
            }}
        }});
        
        // Improved Seamless Update Mechanism
        let secondsLeft = 15;
        const countdownEl = document.getElementById('countdown-box');
        const updateTsEl = document.getElementById('update-ts');

        setInterval(() => {{
            secondsLeft--;
            if (secondsLeft <= 0) {{
                countdownEl.innerText = 'Atualizando agora... 🔄';
                fetch(window.location.href)
                    .then(response => response.text())
                    .then(html => {{
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        
                        // 1. Update Recommendation Card (O mais visual)
                        const oldRec = document.querySelector('.dashboard-grid > div:first-child');
                        const newRec = doc.querySelector('.dashboard-grid > div:first-child');
                        if (oldRec && newRec) oldRec.innerHTML = newRec.innerHTML;

                        // 2. Update Table (Dados discretos)
                        const oldTable = document.querySelector('table tbody');
                        const newTable = doc.querySelector('table tbody');
                        if (oldTable && newTable) oldTable.innerHTML = newTable.innerHTML;

                        // 3. Update Status Header (PID, Rodada)
                        const oldHeader = document.querySelector('.header');
                        const newHeader = doc.querySelector('.header');
                        // Update specific elements to avoid chart re-render issues
                        const oldRound = oldHeader.querySelector('.round-info');
                        const newRound = newHeader.querySelector('.round-info');
                        if (oldRound && newRound) oldRound.innerHTML = newRound.innerHTML;

                        const oldPid = oldHeader.querySelector('.pid-tag');
                        const newPid = newHeader.querySelector('.pid-tag');
                        if (oldPid && newPid) oldPid.innerHTML = newPid.innerHTML;

                        // 4. System Overview Stats
                        const oldStats = document.querySelector('.mini-stats');
                        const newStats = doc.querySelector('.mini-stats');
                        if (oldStats && newStats) oldStats.innerHTML = newStats.innerHTML;

                        // 5. Success Rate Logic for Bars (Requires bar update)
                        // If we had many charts, we'd use chart.update(), 
                        // but for visual simplicity and avoiding memory leaks with Chart.js 
                        // without a full state manager, we'll reload for now IF the chart data changes,
                        // BUT we wrap it in a seamless way.
                        
                        updateTsEl.innerText = doc.getElementById('update-ts').innerText;
                        
                        // Reset countdown
                        secondsLeft = 15;
                        
                        // We do a soft-reload here ONLY to keep Chart.js perfectly synced 
                        // without the white flash (since the page is already in memory)
                        // This handles the complexity of bar chart updates without flicker.
                        window.history.replaceState(null, null, window.location.href);
                        setTimeout(() => window.location.reload(), 100); 
                    }});
            }} else {{
                countdownEl.innerText = `Próxima atualização em ${{secondsLeft}}s`;
            }}
        }}, 1000);
    </script>
</body>
</html>"""

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == "__main__":
    generate_dashboard()
