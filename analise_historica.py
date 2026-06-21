#!/usr/bin/env python3
"""
analise_historica.py — Linkfort Championship Analyzer
Agrupa medições por janela de tempo, rankeia por período e monta
o placar de quem mais ficou no top ao longo do histórico.
"""

import csv
import os
import statistics
from datetime import datetime, timedelta
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "dados_dns_linkfort.csv")
OUTPUT_HTML = os.path.join(BASE_DIR, "historico.html")

# ── Parâmetros ─────────────────────────────────────────────────────────────
WINDOW = "day"   # "day" | "week" | "hour"
TOP_N  = 3       # quantas posições contam como "pódio"


def window_key(ts_str: str) -> str:
    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    if WINDOW == "hour":
        return dt.strftime("%Y-%m-%d %H:00")
    elif WINDOW == "week":
        monday = dt - timedelta(days=dt.weekday())
        return monday.strftime("Semana %d/%m/%Y")
    else:  # day
        return dt.strftime("%d/%m/%Y")


def rank_window(window_data: dict) -> list:
    """Recebe {dns_name: [latencies]}, retorna lista ordenada (rank 1 = melhor)."""
    scores = []
    for name, lats_oks in window_data.items():
        lats, total = lats_oks
        ok = len(lats)
        success_rate = ok / total if total > 0 else 0
        avg_lat = statistics.mean(lats) if lats else 9999
        scores.append((name, success_rate, avg_lat, ok, total))
    # Critério: success_rate DESC, avg_latency ASC
    scores.sort(key=lambda x: (-x[1], x[2]))
    return scores


def load_and_analyze():
    # {window_key: {dns_name: ([ok_latencies], total_count)}}
    windows = defaultdict(lambda: defaultdict(lambda: [[], 0]))

    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            wk = window_key(row["timestamp"])
            name = row["dns_name"]
            latency = float(row["latency_ms"])
            status = row["status"]

            entry = windows[wk][name]
            entry[1] += 1           # total
            if status == "OK":
                entry[0].append(latency)   # ok latencies

    return windows


def compute_championship(windows: dict):
    sorted_windows = sorted(windows.keys(),
                            key=lambda w: datetime.strptime(w, "%d/%m/%Y")
                            if WINDOW == "day" else w)

    # Placar acumulado
    gold   = defaultdict(int)   # 1º lugar
    silver = defaultdict(int)   # 2º lugar
    bronze = defaultdict(int)   # 3º lugar
    podium = defaultdict(int)   # top 3
    total_windows = len(sorted_windows)

    timeline = []  # [(window, ranked_list)]

    for wk in sorted_windows:
        ranked = rank_window(windows[wk])
        timeline.append((wk, ranked))
        if len(ranked) >= 1:
            gold[ranked[0][0]] += 1
            podium[ranked[0][0]] += 1
        if len(ranked) >= 2:
            silver[ranked[1][0]] += 1
            podium[ranked[1][0]] += 1
        if len(ranked) >= 3:
            bronze[ranked[2][0]] += 1
            podium[ranked[2][0]] += 1

    # Todos os DNS vistos
    all_dns = set()
    for _, ranked in timeline:
        for r in ranked:
            all_dns.add(r[0])

    championship = []
    for name in all_dns:
        championship.append({
            "name":   name,
            "gold":   gold[name],
            "silver": silver[name],
            "bronze": bronze[name],
            "podium": podium[name],
            "podium_pct": round(podium[name] / total_windows * 100, 1) if total_windows else 0,
        })
    championship.sort(key=lambda x: (-x["gold"], -x["silver"], -x["bronze"]))

    return championship, timeline, total_windows


def medal_emoji(pos: int) -> str:
    return ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"][min(pos, 7)]


def dns_color(name: str) -> str:
    if "Linkfort" in name: return "#38bdf8"
    if "Google"   in name: return "#facc15"
    if "Cloudflare" in name: return "#fb923c"
    return "#a78bfa"


def generate_html(championship, timeline, total_windows):
    # ── Tabela de campeonato ───────────────────────────────────────────────
    champ_rows = ""
    for i, c in enumerate(championship):
        bar_w = round(c["podium_pct"])
        champ_rows += f"""
        <tr>
            <td><span class="rank-badge" style="background:{dns_color(c['name'])};color:#0f172a">{i+1}</span></td>
            <td style="font-weight:700;color:{dns_color(c['name'])}">{c['name']}</td>
            <td style="font-size:1.4rem">{'🥇' * c['gold']}</td>
            <td>{'🥈' * c['silver']}</td>
            <td>{'🥉' * c['bronze']}</td>
            <td>
                <div style="display:flex;align-items:center;gap:.6rem">
                    <div style="flex:1;background:rgba(255,255,255,.05);border-radius:4px;height:8px">
                        <div style="width:{bar_w}%;background:{dns_color(c['name'])};height:8px;border-radius:4px"></div>
                    </div>
                    <span style="font-size:.85rem;color:#94a3b8;min-width:40px">{c['podium_pct']}%</span>
                </div>
            </td>
        </tr>"""

    # ── Timeline de campeões ───────────────────────────────────────────────
    timeline_rows = ""
    for wk, ranked in timeline:
        cols = ""
        for pos, r in enumerate(ranked[:TOP_N]):
            name, sr, avg_lat, ok, total = r
            cols += f"""<td style="color:{dns_color(name)};font-weight:{'800' if pos==0 else '400'}">
                {medal_emoji(pos)} {name}<br>
                <span style="font-size:.7rem;color:#64748b">{avg_lat:.1f}ms · {sr*100:.0f}%</span>
            </td>"""
        # preenche colunas vazias se necessário
        for _ in range(TOP_N - len(ranked)):
            cols += "<td>—</td>"
        timeline_rows += f"<tr><td style='color:#64748b;font-size:.85rem'>{wk}</td>{cols}</tr>"

    # ── Streak: maior sequência de vitórias ───────────────────────────────
    streak_dns, streak_len, cur_dns, cur_len = None, 0, None, 0
    for _, ranked in timeline:
        winner = ranked[0][0] if ranked else None
        if winner == cur_dns:
            cur_len += 1
        else:
            if cur_len > streak_len:
                streak_len, streak_dns = cur_len, cur_dns
            cur_dns, cur_len = winner, 1
    if cur_len > streak_len:
        streak_len, streak_dns = cur_len, cur_dns

    window_label = {"day": "dias", "week": "semanas", "hour": "horas"}[WINDOW]

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Linkfort — Histórico Campeonato DNS</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: hsl(222,47%,7%); --card: hsla(222,47%,12%,.7);
            --text: hsl(210,40%,98%); --muted: hsl(215,20%,65%);
            --border: hsla(0,0%,100%,.08);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Outfit', sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 2rem;
            min-height: 100vh;
            background-image:
                radial-gradient(circle at 15% 25%, hsla(199,89%,48%,.08) 0%, transparent 40%),
                radial-gradient(circle at 85% 75%, hsla(263,70%,50%,.08) 0%, transparent 40%);
        }}
        h1 {{
            font-size: 2.8rem; font-weight: 800; text-align: center;
            background: linear-gradient(to right, #38bdf8, #818cf8);
            -webkit-background-clip: text; background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: .5rem;
        }}
        .subtitle {{ text-align:center; color:var(--muted); margin-bottom:2.5rem; font-size:1rem; }}
        .card {{
            background: var(--card); backdrop-filter: blur(16px);
            border-radius: 20px; padding: 2rem;
            border: 1px solid var(--border);
            box-shadow: 0 10px 40px -10px rgba(0,0,0,.5);
            margin-bottom: 2rem; max-width: 1100px; margin-inline: auto;
        }}
        h2 {{ font-size:1.2rem; font-weight:600; color:#e2e8f0;
              border-bottom:1px solid var(--border); padding-bottom:.8rem; margin-bottom:1.5rem; }}
        table {{ width:100%; border-collapse:collapse; }}
        th {{ text-align:left; padding:.8rem 1rem; color:var(--muted);
              font-size:.75rem; text-transform:uppercase; letter-spacing:1px;
              border-bottom:1px solid var(--border); }}
        td {{ padding:.8rem 1rem; border-bottom:1px solid rgba(255,255,255,.04);
              font-size:.95rem; vertical-align:middle; }}
        tr:last-child td {{ border-bottom: none; }}
        .rank-badge {{
            display:inline-flex; align-items:center; justify-content:center;
            width:26px; height:26px; border-radius:50%;
            font-weight:800; font-size:.8rem;
        }}
        .stat-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:1.5rem; margin-bottom:2rem; max-width:1100px; margin-inline:auto; }}
        .stat-box {{
            background:var(--card); border:1px solid var(--border);
            border-radius:16px; padding:1.5rem; text-align:center;
        }}
        .stat-val {{ font-size:2.2rem; font-weight:800; color:#38bdf8; }}
        .stat-lbl {{ font-size:.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:1px; margin-top:.3rem; }}
        @media(max-width:640px) {{ .stat-grid {{ grid-template-columns:1fr; }} }}
    </style>
</head>
<body>
    <h1>🏆 Linkfort Championship</h1>
    <p class="subtitle">Análise histórica por {window_label} · {total_windows} períodos · {len(championship)} competidores</p>

    <div class="stat-grid">
        <div class="stat-box">
            <div class="stat-val" style="color:{dns_color(championship[0]['name']) if championship else '#38bdf8'}">{championship[0]['name'] if championship else '—'}</div>
            <div class="stat-lbl">🥇 Maior Campeão ({championship[0]['gold']} ouros)</div>
        </div>
        <div class="stat-box">
            <div class="stat-val" style="color:#facc15">{streak_len}</div>
            <div class="stat-lbl">🔥 Maior Streak de Vitórias ({streak_dns})</div>
        </div>
        <div class="stat-box">
            <div class="stat-val">{total_windows}</div>
            <div class="stat-lbl">📅 Períodos analisados ({window_label})</div>
        </div>
    </div>

    <div class="card">
        <h2>🏅 Tabela de Campeonato — Quem mais ficou no Top?</h2>
        <table>
            <thead>
                <tr>
                    <th>Pos</th><th>Servidor DNS</th>
                    <th>🥇 Ouros</th><th>🥈 Pratas</th><th>🥉 Bronzes</th>
                    <th>Tempo no Pódio (top {TOP_N})</th>
                </tr>
            </thead>
            <tbody>{champ_rows}</tbody>
        </table>
    </div>

    <div class="card">
        <h2>📅 Timeline — Campeões por {window_label.rstrip('s')}</h2>
        <div style="overflow-x:auto">
        <table>
            <thead>
                <tr>
                    <th>Período</th>
                    <th>🥇 1º</th><th>🥈 2º</th><th>🥉 3º</th>
                </tr>
            </thead>
            <tbody>{timeline_rows}</tbody>
        </table>
        </div>
    </div>
</body>
</html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    return OUTPUT_HTML


def print_terminal(championship, timeline, total_windows):
    window_label = {"day": "dias", "week": "semanas", "hour": "horas"}[WINDOW]
    print(f"\n{'='*65}")
    print(f"  🏆  LINKFORT CHAMPIONSHIP — análise por {window_label}")
    print(f"  {total_windows} períodos · {len(championship)} competidores")
    print(f"{'='*65}")
    print(f"\n{'POS':<4} {'SERVIDOR':<20} {'🥇':>5} {'🥈':>5} {'🥉':>5} {'PÓDIO%':>8}")
    print("-" * 55)
    for i, c in enumerate(championship):
        print(f"{i+1:<4} {c['name']:<20} {c['gold']:>5} {c['silver']:>5} {c['bronze']:>5} {c['podium_pct']:>7.1f}%")

    print(f"\n{'='*65}")
    print(f"  📅  TIMELINE DE CAMPEÕES (últimos 10 períodos)")
    print(f"{'='*65}")
    for wk, ranked in timeline[-10:]:
        top = ranked[0] if ranked else None
        if top:
            name, sr, avg_lat, ok, total = top
            print(f"  {wk}  →  🥇 {name:<20} {avg_lat:6.1f}ms  {sr*100:.0f}% ok")


if __name__ == "__main__":
    if not os.path.exists(CSV_FILE):
        print("❌ CSV não encontrado:", CSV_FILE)
        exit(1)

    print(f"📊 Carregando dados de {CSV_FILE}...")
    windows = load_and_analyze()
    championship, timeline, total_windows = compute_championship(windows)

    print_terminal(championship, timeline, total_windows)

    out = generate_html(championship, timeline, total_windows)
    print(f"\n✅ Relatório HTML gerado: {out}")
    print(f"   Abra no browser: file://{out}\n")
