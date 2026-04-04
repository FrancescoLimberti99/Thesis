const API_BASE = 'http://localhost:8000/api';

// SLIDESHOW
let currentSlide = 0;
const slides = document.querySelectorAll('.slide');

function nextSlide() {
    currentSlide = (currentSlide + 1) % slides.length;
    slides.forEach(slide => slide.classList.remove('active'));
    slides[currentSlide].classList.add('active');
}

setInterval(nextSlide, 10000);

// ELEMENTI UI
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');
const culturalCard = document.getElementById('culturalCard');
const attachBtn = document.getElementById('attachBtn');
const chatFileInput = document.getElementById('chatFileInput');
const chatImagePreview = document.getElementById('chatImagePreview');
const chatPreviewImg = document.getElementById('chatPreviewImg');
const chatRemoveBtn = document.getElementById('chatRemoveBtn');

let chatUploadedFile = null;
let currentArtwork = null;
let conversationHistory = [];

// AVVIO
window.addEventListener('DOMContentLoaded', () => {
    const inputType = sessionStorage.getItem('inputType');
    const userMessage = sessionStorage.getItem('userMessage');
    const uploadedImage = sessionStorage.getItem('uploadedImage');
    const gallerySelected = sessionStorage.getItem('gallerySelected');

    sessionStorage.clear();

    if (inputType === 'image' && uploadedImage) {
        culturalCard.style.display = 'none';
        fetch(uploadedImage)
            .then(r => r.blob())
            .then(blob => {
                const file = new File([blob], 'image.jpg', { type: 'image/jpeg' });
                addUserMessageWithImage(uploadedImage, userMessage || '');
                sendToBackend(userMessage || '', file);
            });
    } else if (gallerySelected === 'true' && userMessage) {
        currentArtwork = userMessage;
        addBotMessage(`Cosa vuoi sapere su ${userMessage}?`);
        conversationHistory.push({ role: 'user', content: `Voglio sapere informazioni su ${userMessage}` });
        conversationHistory.push({ role: 'assistant', content: `Cosa vuoi sapere su ${userMessage}?` });
        updateCulturalCard(userMessage, null);
    } else if (inputType === 'text' && userMessage) {
        culturalCard.style.display = 'none';
        addUserMessage(userMessage);
        sendToBackend(userMessage, null);
    } else {
        culturalCard.style.display = 'none';
        addBotMessage('Ciao! Puoi scrivermi il nome di un\'opera o caricare una foto per iniziare.');
    }
});

// UPLOAD IMMAGINE IN CHAT
attachBtn.addEventListener('click', () => chatFileInput.click());

chatFileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleChatFile(e.target.files[0]);
});

function handleChatFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('Per favore carica solo immagini!');
        return;
    }
    chatUploadedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        chatPreviewImg.src = e.target.result;
        chatImagePreview.style.display = 'flex';
    };
    reader.readAsDataURL(file);
}

chatRemoveBtn.addEventListener('click', () => {
    chatUploadedFile = null;
    chatFileInput.value = '';
    chatPreviewImg.src = '';
    chatImagePreview.style.display = 'none';
});

// INVIO MESSAGGIO
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

function sendMessage() {
    const message = chatInput.value.trim();
    if (!message && !chatUploadedFile) return;

    if (chatUploadedFile) {
        const file = chatUploadedFile;
        const text = message;
        const reader = new FileReader();
        reader.onload = (e) => addUserMessageWithImage(e.target.result, text);
        reader.readAsDataURL(file);
        chatUploadedFile = null;
        chatFileInput.value = '';
        chatImagePreview.style.display = 'none';
        chatInput.value = '';
        sendToBackend(text, file);
    } else {
        addUserMessage(message);
        chatInput.value = '';
        sendToBackend(message, null);
    }
}

// CHIAMATA BACKEND
async function sendToBackend(text, imageFile) {
    showTypingIndicator();

    const formData = new FormData();
    if (text) formData.append('text', text);
    if (imageFile) formData.append('image', imageFile);
    if (currentArtwork) formData.append('current_artwork', currentArtwork);
    formData.append('history', JSON.stringify(conversationHistory));

    try {
        const response = await fetch(`${API_BASE}/chat/`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        hideTypingIndicator();

        if (response.ok) {
            if (data.metadata_match) {
                const campoLabel = {
                    'autore': "dell'autore",
                    'epoca': "dell'epoca",
                    'stile': "dello stile",
                    'localita': "della località",
                }[data.campo] || 'del campo';
                const msg = data.opere.length === 1
                    ? `Ho trovato 1 opera ${campoLabel} "${data.valore}". Vuoi saperne di più?`
                    : `Ho trovato ${data.opere.length} opere ${campoLabel} "${data.valore}". Selezionane una:`;
                addBotMessage(msg);
                offerMetadataResults(data.opere);
                return;
            }
            const newArtwork = data.artwork;
            const extraArtworks = data.extra_artworks || [];

            // CASO: più opere rilevate (domanda comparativa o prima volta)
            if (extraArtworks.length > 0 && !currentArtwork) {
                // risponde alla domanda comparativa
                addBotMessage(data.response);
                // chiede di quale opera vuole parlare
                askArtworkChoice([newArtwork, ...extraArtworks]);
            } else if (extraArtworks.length > 0 && currentArtwork) {
                // siamo già in una chat con un'opera: risponde e propone nuova chat
                addBotMessage(data.response);
                // includi anche newArtwork se diverso da currentArtwork
                const allOtherArtworks = [...new Set(
                    [newArtwork, ...extraArtworks].filter(o => o !== currentArtwork)
                )];
                if (allOtherArtworks.length > 0) {
                    offerNewChat(allOtherArtworks);
                }
                // aggiorna cronologia senza cambiare opera corrente
                conversationHistory.push({ role: 'user', content: text || '[Immagine caricata - opera riconosciuta: ' + newArtwork + ']' });
                conversationHistory.push({ role: 'assistant', content: data.response });
            } else {
                // CASO NORMALE: 1 opera
                if (newArtwork && newArtwork !== currentArtwork) {
                    // nuova opera riconosciuta
                    if (currentArtwork) {
                        // opera diversa citata durante conversazione esistente
                        addBotMessage(data.response);
                        offerNewChat([newArtwork]);
                        conversationHistory.push({ role: 'user', content: text || '[Immagine caricata - opera riconosciuta: ' + newArtwork + ']' });
                        conversationHistory.push({ role: 'assistant', content: data.response });
                    } else {
                        // prima opera della chat
                        currentArtwork = newArtwork;
                        updateCulturalCard(newArtwork, imageFile);
                        addBotMessage(data.response);
                        conversationHistory.push({ role: 'user', content: text || '[Immagine caricata - opera riconosciuta: ' + newArtwork + ']' });
                        conversationHistory.push({ role: 'assistant', content: data.response });
                    }
                } else {
                    // stessa opera, risposta normale
                    addBotMessage(data.response);
                    conversationHistory.push({ role: 'user', content: text || 'Immagine caricata' });
                    conversationHistory.push({ role: 'assistant', content: data.response });
                }
            }
        } else {
            addBotMessage(data.response || 'Si è verificato un errore. Riprova.');
        }
    } catch (error) {
        hideTypingIndicator();
        addBotMessage('Errore di connessione. Il server è avviato?');
    }
}

// CHIEDI SCELTA OPERA
function askArtworkChoice(artworks) {
    const div = document.createElement('div');
    div.className = 'message bot-message';
    let btns = artworks.map(a =>
        `<button class="artwork-choice-btn" onclick="selectArtwork('${a.replace(/'/g, "\\'")}')">${a}</button>`
    ).join('');
    div.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <p>Di quale opera vuoi continuare a parlare?</p>
            <div style="margin-top:8px;">${btns}</div>
        </div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function selectArtwork(artworkName) {
    // disabilita tutti i bottoni di scelta dopo la selezione
    document.querySelectorAll('.artwork-choice-btn').forEach(btn => {
        btn.disabled = true;
    });
    currentArtwork = artworkName;
    updateCulturalCard(artworkName, null);
    addBotMessage(`Perfetto! Parliamo di ${artworkName}. Cosa vuoi sapere?`);
    conversationHistory.push({ role: 'assistant', content: `Parliamo di ${artworkName}. Cosa vuoi sapere?` });
}

// OFFRI RISULTATI METADATA (autore/epoca/stile/località)
function offerMetadataResults(opere) {
    const div = document.createElement('div');
    div.className = 'message bot-message';
    const btns = opere.map(a =>
        `<button class="artwork-choice-btn" onclick="openNewChat('${a.replace(/'/g, "\\'")}')">${a}</button>`
    ).join('');
    div.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">${btns}</div>
        </div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

// OFFRI NUOVA CHAT
function offerNewChat(artworks) {
    const div = document.createElement('div');
    div.className = 'message bot-message';
    let btns = artworks.map(a =>
        `<button class="new-chat-btn" onclick="openNewChat('${a.replace(/'/g, "\\'")}')">Apri una chat su ${a}</button>`
    ).join('');
    const label = artworks.length > 1
        ? 'Ho rilevato altre opere. Vuoi aprire una nuova chat?'
        : "Ho rilevato un'altra opera. Vuoi aprire una nuova chat?";
    div.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <p>${label}</p>
            <div style="margin-top:8px;">${btns}</div>
        </div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function openNewChat(artworkName) {
    sessionStorage.setItem('inputType', 'text');
    sessionStorage.setItem('userMessage', artworkName);
    sessionStorage.setItem('gallerySelected', 'true');
    window.location.href = 'chat.html';
}

// AGGIORNA CARD OPERA
async function updateCulturalCard(artworkName, imageFile) {
    culturalCard.style.display = 'flex';

    document.getElementById('cardTitle').textContent = artworkName;
    document.getElementById('cardEpoch').textContent = 'Caricamento...';
    document.getElementById('cardStyle').textContent = 'Caricamento...';
    document.getElementById('cardLocation').textContent = 'Caricamento...';
    document.getElementById('cardAuthor').textContent = 'Caricamento...';

    if (imageFile) {
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('recognizedImage').src = e.target.result;
        };
        reader.readAsDataURL(imageFile);
    }

    try {
        const response = await fetch(`${API_BASE}/artworks/`, { credentials: 'include' });
        const artworks = await response.json();
        const artwork = artworks.find(a => a.name === artworkName);

        if (artwork) {
            document.getElementById('cardTitle').textContent = artwork.name;
            document.getElementById('cardEpoch').textContent = artwork.period || '—';
            document.getElementById('cardStyle').textContent = artwork.style || '—';
            document.getElementById('cardLocation').textContent = artwork.location || '—';
            document.getElementById('cardAuthor').textContent = artwork.author || '—';
            document.getElementById('cardContext').textContent = artwork.context || '—';

            if (!imageFile && artwork.images && artwork.images.length > 0) {
                document.getElementById('recognizedImage').src = 'http://localhost:8000' + artwork.images[0].image;
            }
        }
    } catch (error) {
        console.error('Errore recupero dettagli opera:', error);
    }
}

// MESSAGGI
function addUserMessage(text) {
    const div = document.createElement('div');
    div.className = 'message user-message';
    div.innerHTML = `
        <div class="message-avatar">👤</div>
        <div class="message-content"><p>${escapeHtml(text)}</p></div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function addUserMessageWithImage(imageData, text) {
    const div = document.createElement('div');
    div.className = 'message user-message';
    div.innerHTML = `
        <div class="message-avatar">👤</div>
        <div class="message-content">
            <img src="${imageData}" style="max-width:200px;border-radius:8px;margin-bottom:8px;">
            ${text ? `<p>${escapeHtml(text)}</p>` : ''}
        </div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function addBotMessage(text) {
    const div = document.createElement('div');
    div.className = 'message bot-message';
    div.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content"><p>${text}</p></div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function showTypingIndicator() {
    typingIndicator.style.display = 'flex';
    scrollToBottom();
}

function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// NAVIGAZIONE
document.getElementById('backBtn').addEventListener('click', () => {
    window.location.href = 'index.html';
});

document.getElementById('logoutBtn').addEventListener('click', async () => {
    await fetch(`${API_BASE}/logout/`, { method: 'POST', credentials: 'include' });
    window.location.href = 'index.html';
});