// --- CONFIGURAÇÃO ---
// Se estiver rodando no Vercel, cole o link do seu Ngrok aqui abaixo:
const API_URL = "https://noncircuitous-towerless-mozell.ngrok-free.dev"; // Ex: "https://abcd-123.ngrok-free.app"

// Inicializar ícones do Lucide
lucide.createIcons();

async function updateStatus() {
    try {
        const response = await fetch(`${API_URL}/api/status`);
        const data = await response.json();

        // Atualiza título da música
        document.getElementById('song-title').innerText = data.tocando;
        
        // Atualiza status de conexão
        const statusBadge = document.getElementById('connection-status');
        const dot = statusBadge.querySelector('.dot');
        
        if (data.status.includes("Tocando") || data.status.includes("Parado")) {
            statusBadge.innerHTML = `<span class="dot online"></span> ${data.status}`;
        } else {
            statusBadge.innerHTML = `<span class="dot"></span> ${data.status}`;
        }

        // Atualiza Fila
        const queueList = document.getElementById('queue-list');
        const queueCount = document.getElementById('queue-count');
        queueCount.innerText = `${data.fila.length} músicas`;
        
        queueList.innerHTML = '';
        data.fila.forEach((musica, index) => {
            const li = document.createElement('li');
            li.className = 'queue-item';
            li.innerHTML = `
                <span class="item-index">${String(index + 1).padStart(2, '0')}</span>
                <span class="item-title">${musica}</span>
                <i data-lucide="music" style="width: 14px; opacity: 0.5"></i>
            `;
            queueList.appendChild(li);
        });
        
        lucide.createIcons(); // Re-renderiza ícones novos

    } catch (error) {
        console.error("Erro ao buscar status:", error);
        document.getElementById('connection-status').innerText = "Erro de conexão";
    }
}

async function sendCommand(action, data = null) {
    try {
        const response = await fetch(`${API_URL}/api/comando`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, data })
        });
        
        if (response.ok) {
            showToast(action === 'add' ? "Música adicionada!" : "Comando enviado!");
            if (action === 'add') document.getElementById('music-input').value = '';
        }
    } catch (error) {
        showToast("Erro ao enviar comando");
    }
}

function addMusic() {
    const input = document.getElementById('music-input');
    if (input.value.trim() !== "") {
        sendCommand('add', input.value.trim());
    }
}

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// Atalho Enter para busca
document.getElementById('music-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') addMusic();
});

// Update automático a cada 3 segundos
setInterval(updateStatus, 3000);
updateStatus();
