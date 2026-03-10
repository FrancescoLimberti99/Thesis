const API_BASE = 'http://localhost:8000/api';

// SLIDESHOW
let currentSlide = 0;
const slides = document.querySelectorAll('.slide');

function nextSlide() {
    slides[currentSlide].classList.remove('active');
    currentSlide = (currentSlide + 1) % slides.length;
    slides[currentSlide].classList.add('active');
}

setInterval(nextSlide, 10000);

// LOGOUT
document.getElementById('logoutBtn').addEventListener('click', async () => {
    await fetch(`${API_BASE}/logout/`, { method: 'POST' });
    window.location.href = 'index.html';
});

// DATI
let allConversations = [];

// CARICA CONVERSAZIONI
async function loadConversations() {
    try {
        const response = await fetch(`${API_BASE}/conversations/`, {
            credentials: 'include'
        });
        allConversations = await response.json();
        renderConversations(allConversations);
    } catch (error) {
        document.getElementById('conversationList').innerHTML =
            '<p class="loading-msg">Errore nel caricamento delle conversazioni.</p>';
    }
}

function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('it-IT', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function renderConversations(conversations) {
    const list = document.getElementById('conversationList');

    if (conversations.length === 0) {
        list.innerHTML = '<p class="loading-msg">Nessuna conversazione ancora.</p>';
        return;
    }

    list.innerHTML = conversations.map(conv => `
        <div class="conversation-item">
            <div class="conversation-header">
                <span class="conversation-artwork">${conv.recognized_artwork}</span>
                <div style="display:flex; gap:10px; align-items:center;">
                    <span class="similarity-badge">Punteggio: ${(conv.similarity_score * 100).toFixed(1)}%</span>
                    <span class="conversation-timestamp">${formatDate(conv.timestamp)}</span>
                </div>
            </div>
            <div class="conversation-body">
                <p class="conversation-input">
                    <span>Domanda:</span> ${conv.input_text || ''}
                    ${conv.input_image ? `<img src="http://localhost:8000/media/${conv.input_image}" style="max-width:150px; max-height:120px; border-radius:8px; margin-top:6px; border:2px solid #d4af37;">` : ''}
                </p>
                <p class="conversation-response">
                    <span>Risposta:</span> ${conv.model_response}
                </p>
            </div>
        </div>
    `).join('');
}

// RICERCA
document.getElementById('searchInput').addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    const filtered = allConversations.filter(conv =>
        conv.recognized_artwork.toLowerCase().includes(query)
    );
    renderConversations(filtered);
});

// ORDINAMENTO
document.getElementById('sortSelect').addEventListener('change', (e) => {
    const sorted = [...allConversations].sort((a, b) => {
        if (e.target.value === 'newest') {
            return new Date(b.timestamp) - new Date(a.timestamp);
        } else {
            return new Date(a.timestamp) - new Date(b.timestamp);
        }
    });
    renderConversations(sorted);
});

// AVVIO
loadConversations();