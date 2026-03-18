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
const attachBtn = document.getElementById('attachBtn');
const chatFileInput = document.getElementById('chatFileInput');
const chatImagePreview = document.getElementById('chatImagePreview');
const chatPreviewImg = document.getElementById('chatPreviewImg');
const chatRemoveBtn = document.getElementById('chatRemoveBtn');

let chatUploadedFile = null;
let pendingImageFile = null;
let pendingText = null;
let pendingInputType = null;

// AVVIO — primo messaggio da index.html tramite sessionStorage
window.addEventListener('DOMContentLoaded', () => {
    const inputType = sessionStorage.getItem('inputType');
    const userMessage = sessionStorage.getItem('userMessage');
    const uploadedImage = sessionStorage.getItem('uploadedImage');
    const gallerySelected = sessionStorage.getItem('gallerySelected');

    console.log('inputType:', sessionStorage.getItem('inputType'));
    console.log('userMessage:', sessionStorage.getItem('userMessage'));
    sessionStorage.clear();

    if (inputType === 'image' && uploadedImage) {
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
    } else if (inputType === 'text' && userMessage) {
            addUserMessage(userMessage);
        sendToBackend(userMessage, null);
    } else {
            addBotMessage('Ciao! Puoi scrivermi il nome di un\'opera o caricare una foto per iniziare.');
    }
});

// UPLOAD IMMAGINE IN CHAT
attachBtn.addEventListener('click', () => chatFileInput.click());

chatFileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleChatFile(e.target.files[0]);
    }
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

        // mostra messaggio utente con immagine
        const reader = new FileReader();
        reader.onload = (e) => {
            addUserMessageWithImage(e.target.result, text);
        };
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

let currentArtwork = null;
let conversationHistory = [];

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
            if (data.artwork) {
                currentArtwork = data.artwork; // aggiorna opera corrente
            }
            
            // aggiorna cronologia
            conversationHistory.push({
                role: 'user',
                content: text || 'Immagine caricata'
            });
            conversationHistory.push({
                role: 'assistant',
                content: data.response
            });

            addBotMessage(data.response);
        } else {
            addBotMessage(data.response || 'Si è verificato un errore. Riprova.');
        }
    } catch (error) {
        hideTypingIndicator();
        addBotMessage('Errore di connessione. Il server è avviato?');
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
    await fetch(`${API_BASE}/logout/`, {
        method: 'POST',
        credentials: 'include'
    });
    window.location.href = 'index.html';
});