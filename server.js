#!/usr/bin/env node
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const PORT = 3000;
const BASE_DIR = __dirname;
const HTML_FILE = path.join(BASE_DIR, 'dashboard.html');
const HISTORICO_FILE = path.join(BASE_DIR, 'historico.html');
const ANALISE_SCRIPT = path.join(BASE_DIR, 'analise_historica.py');
const MONITOR_SCRIPT = path.join(BASE_DIR, 'monitor_dados.sh');

let monitorProcess = null;

console.log(`\n==========================================`);
console.log(`🚀 Linkfort Orchestrator v2.0`);
console.log(`==========================================\n`);

const startMonitor = () => {
    console.log(`📡 Iniciando monitoramento em background...`);
    // Iniciamos com --silent para não poluir o terminal com pontos
    monitorProcess = spawn('bash', [MONITOR_SCRIPT, '--silent'], {
        cwd: BASE_DIR,
        stdio: 'inherit'
    });

    monitorProcess.on('error', (err) => {
        console.error(`❌ Erro no monitor: ${err.message}`);
    });

    monitorProcess.on('exit', (code) => {
        if (code !== 0 && code !== null) {
            console.log(`⚠️ Monitor fechado com código ${code}. Reiniciando em 5s...`);
            setTimeout(startMonitor, 5000);
        }
    });
};

const server = http.createServer((req, res) => {
    if (req.url === '/' || req.url === '/dashboard.html') {
        fs.readFile(HTML_FILE, (err, content) => {
            if (err) {
                res.writeHead(404);
                res.end('<h1>Dashboard inicializando...</h1><p>Aguarde a primeira rodada do monitor.</p>');
            } else {
                res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
                res.end(content);
            }
        });
    } else if (req.url === '/export') {
        const reportPath = path.join(BASE_DIR, 'linkfort_report.txt');
        fs.readFile(reportPath, (err, data) => {
            if (err) {
                res.writeHead(404);
                res.end('Relatório ainda não gerado. Aguarde a próxima atualização.');
            } else {
                res.writeHead(200, {
                    'Content-Type': 'text/plain; charset=utf-8',
                    'Content-Disposition': 'attachment; filename="linkfort_report.txt"'
                });
                res.end(data);
            }
        });
    } else if (req.url === '/historico') {
        // Regenera o historico.html e serve
        const { execFile } = require('child_process');
        execFile('python3', [ANALISE_SCRIPT], { cwd: BASE_DIR }, (err) => {
            if (err) console.error('⚠️  Erro ao gerar histórico:', err.message);
            fs.readFile(HISTORICO_FILE, (err2, content) => {
                if (err2) {
                    res.writeHead(404);
                    res.end('<h1>Histórico ainda não disponível.</h1><p>Aguarde dados no CSV.</p>');
                } else {
                    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
                    res.end(content);
                }
            });
        });
    } else if (req.url === '/stop') {
        res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end('Desligando sistema linkfort...');
        console.log('🛑 Comando de parada recebido via Web Interface.');
        setTimeout(cleanup, 1000);
    } else {
        res.writeHead(404);
        res.end('<h1>404</h1>');
    }
});

server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
        console.error(`❌ Erro: A porta ${PORT} já está em uso.`);
        console.error(`👉 Tente rodar: pkill -f "node server.js"`);
        process.exit(1);
    }
});

server.listen(PORT, () => {
    // DEPOIS — OSC 8 hyperlink (funciona no GNOME Terminal, Kitty, etc.)
    const url = `http://localhost:${PORT}`;
    const link = `\x1b]8;;${url}\x07${url}\x1b]8;;\x07`;
    console.log(`🌐 Servidor ativo: ${link}`);
    console.log(`📄 Relatório disponível em: \x1b]8;;http://localhost:${PORT}/export\x07http://localhost:${PORT}/export\x1b]8;;\x07`);
    console.log(`🏆 Histórico campeonato: \x1b]8;;http://localhost:${PORT}/historico\x07http://localhost:${PORT}/historico\x1b]8;;\x07`);
    console.log(`🛑 Pressione Ctrl+C para desligar tudo.\n`);
    startMonitor();
});

// Limpeza garantida de processos
const cleanup = () => {
    console.log(`\n\n🧹 Limpando processos Linkfort...`);
    if (monitorProcess) {
        monitorProcess.kill('SIGTERM');
    }
    server.close(() => {
        console.log(`✅ Tudo desligado. Até logo!\n`);
        process.exit(0);
    });
};

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
// Garantia extra para o caso do node ser morto abruptamente
process.on('exit', () => {
    if (monitorProcess) monitorProcess.kill('SIGTERM');
});
