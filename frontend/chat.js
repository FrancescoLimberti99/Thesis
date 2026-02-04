// SLIDESHOW AUTOMATICO
let currentSlide = 0;
const slides = document.querySelectorAll('.slide');

function showSlide(index) {
    slides.forEach(slide => slide.classList.remove('active'));
    slides[index].classList.add('active');
}

function nextSlide() {
    currentSlide = (currentSlide + 1) % slides.length;
    showSlide(currentSlide);
}

setInterval(nextSlide, 10000);

// GESTIONE DATI DA HOMEPAGE
window.addEventListener('DOMContentLoaded', () => {
    const uploadedImageData = localStorage.getItem('uploadedImage');
    const userMessage = localStorage.getItem('userMessage');
    const inputType = localStorage.getItem('inputType'); // 'image' o 'text'
    
    const culturalCard = document.getElementById('culturalCard');
    const chatMessages = document.getElementById('chatMessages');
    
    // GESTIONE BIFORCAZIONE: immagine vs testo
    if (inputType === 'image') {
        // CASO 1: immagine
        
        // card del bene culturale
        culturalCard.style.display = 'flex';
        
        // mostra l'immagine caricata
        if (uploadedImageData) {
            document.getElementById('recognizedImage').src = uploadedImageData;
        }
        
        // messaggio iniziale del bot sul riconoscimento
        chatMessages.innerHTML = `
            <div class="message bot-message">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <p>Ho riconosciuto il <strong>Colosseo</strong>! È uno dei monumenti più iconici di Roma. Cosa vorresti sapere?</p>
                </div>
            </div>
        `;
        
        if (userMessage) {
            setTimeout(() => {
                addUserMessage(userMessage);
                showTypingIndicator();
                setTimeout(() => {
                    hideTypingIndicator();
                    simulateBotResponse(userMessage, 'image');
                }, 1500);
            }, 500);
        }
        
    } else if (inputType === 'text') {
        // CASO 2: solo testo
        
        // nascondo card del bene culturale
        culturalCard.style.display = 'none';
        
        // messaggio di benvenuto generico
        chatMessages.innerHTML = `
            <div class="message bot-message">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <p>Ciao! Sono qui per rispondere alle tue domande sui beni culturali. Come posso aiutarti?</p>
                </div>
            </div>
        `;
        
        if (userMessage) {
            setTimeout(() => {
                addUserMessage(userMessage);
                showTypingIndicator();
                setTimeout(() => {
                    hideTypingIndicator();
                    simulateBotResponse(userMessage, 'text');
                }, 1500);
            }, 500);
        }
    }
    
    // pulisci localStorage
    localStorage.removeItem('uploadedImage');
    localStorage.removeItem('userMessage');
    localStorage.removeItem('inputType');
});

// FUNZIONALITÀ CHAT
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');

// ===== GESTIONE UPLOAD IMMAGINE IN CHAT =====
const chatFileInput = document.getElementById('chatFileInput');
const attachBtn = document.getElementById('attachBtn');
const chatImagePreview = document.getElementById('chatImagePreview');
const chatPreviewImg = document.getElementById('chatPreviewImg');
const chatRemoveBtn = document.getElementById('chatRemoveBtn');
let chatUploadedFile = null;

// click sul bottone allega
attachBtn.addEventListener('click', () => {
    chatFileInput.click();
});

// gestione file selezionato
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
    
    // preview
    const reader = new FileReader();
    reader.onload = (e) => {
        chatPreviewImg.src = e.target.result;
        chatImagePreview.style.display = 'flex';
    };
    reader.readAsDataURL(file);
}

// rimuovi immagine dalla preview
chatRemoveBtn.addEventListener('click', () => {
    chatUploadedFile = null;
    chatFileInput.value = '';
    chatPreviewImg.src = '';
    chatImagePreview.style.display = 'none';
});

// invia messaggio con ENTER
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// invia messaggio con click
sendBtn.addEventListener('click', sendMessage);

function sendMessage() {
    const message = chatInput.value.trim();
    
    if (!message && !chatUploadedFile) return;
    
    // immagine
    if (chatUploadedFile) {
        sendImageMessage(chatUploadedFile, message);
        
        // pulisci
        chatUploadedFile = null;
        chatFileInput.value = '';
        chatImagePreview.style.display = 'none';
        chatInput.value = '';
    } else {
        // solo testo
        addUserMessage(message);
        chatInput.value = '';
        
        showTypingIndicator();
        setTimeout(() => {
            hideTypingIndicator();
            const culturalCard = document.getElementById('culturalCard');
            const context = culturalCard.style.display === 'none' ? 'text' : 'image';
            simulateBotResponse(message, context);
        }, 1500);
    }
}

function sendImageMessage(file, text = '') {
    const reader = new FileReader();
    reader.onload = (e) => {
        const imageData = e.target.result;
        
        // messaggio utente con immagine
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';
        messageDiv.innerHTML = `
            <div class="message-avatar">👤</div>
            <div class="message-content">
                <img src="${imageData}" style="max-width: 200px; border-radius: 8px; margin-bottom: 8px;">
                ${text ? `<p>${escapeHtml(text)}</p>` : ''}
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
        
        // simula riconoscimento immagine
        showTypingIndicator();
        setTimeout(() => {
            hideTypingIndicator();
            
            // aggiorna la card con il nuovo bene riconosciuto
            updateCulturalCard(imageData);
            
            // risposta bot sul riconoscimento
            const botResponse = text 
                ? `Ho riconosciuto un nuovo bene culturale nell'immagine! ${text ? 'Riguardo alla tua domanda: ' + getResponseForQuestion(text) : ''}`
                : 'Ho riconosciuto un nuovo bene culturale nell\'immagine! Cosa vorresti sapere?';
            
            addBotMessage(botResponse);
            
        }, 2000);
    };
    reader.readAsDataURL(file);
}

function updateCulturalCard(imageData, culturalGood = null) {
    const culturalCard = document.getElementById('culturalCard');
    
    // mostra card se era nascosta
    culturalCard.style.display = 'flex';
    
    // aggiorna immagine
    document.getElementById('recognizedImage').src = imageData;
    
    // se ci sono dati del bene, aggiornali (altrimenti usa dati di esempio)
    if (culturalGood) {
        document.getElementById('cardTitle').textContent = culturalGood.name;
        document.getElementById('cardEpoch').textContent = culturalGood.epoch;
        document.getElementById('cardStyle').textContent = culturalGood.style;
        document.getElementById('cardLocation').textContent = culturalGood.location;
        document.getElementById('cardAuthor').textContent = culturalGood.author;
    } else {
        // simulazione - da sostituire con dati reali dal backend
        document.getElementById('cardTitle').textContent = 'Bene Culturale Riconosciuto';
        document.getElementById('cardEpoch').textContent = 'In elaborazione...';
        document.getElementById('cardStyle').textContent = 'In elaborazione...';
        document.getElementById('cardLocation').textContent = 'Italia';
        document.getElementById('cardAuthor').textContent = 'Sconosciuto';
    }
}

function getResponseForQuestion(question) {
    // risposta semplice alla domanda (da migliorare con backend)
    const lowerQ = question.toLowerCase();
    if (lowerQ.includes('quando')) return 'La datazione verrà determinata dall\'analisi.';
    if (lowerQ.includes('dove')) return 'Il bene si trova in Italia, verificherò la località esatta.';
    return 'Sto analizzando l\'immagine per rispondere alla tua domanda.';
}

function addUserMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    messageDiv.innerHTML = `
        <div class="message-avatar">👤</div>
        <div class="message-content">
            <p>${escapeHtml(text)}</p>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function addBotMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <p>${text}</p>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
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

// Escape HTML per sicurezza
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// SIMULAZIONE RISPOSTA BOT
function simulateBotResponse(userMessage, context = 'image') {
    let response;
    
    if (context === 'image') {
        // risposte specifiche sul bene riconosciuto (Colosseo)
        const imageResponses = {
            'quando': 'Il Colosseo fu costruito tra il 70 e l\'80 d.C. sotto gli imperatori Vespasiano e Tito.',
            'chi': 'Il Colosseo fu commissionato dagli imperatori della dinastia Flavia: Vespasiano e suo figlio Tito.',
            'dove': 'Il Colosseo si trova nel centro di Roma, vicino al Foro Romano e al Palatino.',
            'perché': 'Fu costruito come anfiteatro per spettacoli pubblici, combattimenti di gladiatori e cacce di animali.',
            'dimensioni': 'Il Colosseo è lungo 189 metri, largo 156 metri e alto 48 metri. Poteva contenere circa 50.000 spettatori.',
            'storia': 'Il Colosseo è il più grande anfiteatro del mondo romano. Nel Medioevo fu utilizzato come cava di materiali, ma rimane uno dei simboli di Roma.',
        };
        
        response = 'Questa è un\'informazione interessante sul Colosseo! Posso dirti di più sulla sua storia, architettura o importanza culturale.';
        
        const lowerMessage = userMessage.toLowerCase();
        for (const [key, value] of Object.entries(imageResponses)) {
            if (lowerMessage.includes(key)) {
                response = value;
                break;
            }
        }
        
    } else {
        // risposte generiche per domande testuali
        const textResponses = {
            'colosseo': 'Il Colosseo è uno dei monumenti più famosi al mondo! Vuoi sapere qualcosa di specifico? Ad esempio quando fu costruito, chi lo commissionò, o le sue dimensioni?',
            'roma': 'Roma è una città ricchissima di beni culturali! Ci sono il Colosseo, il Pantheon, la Fontana di Trevi, il Foro Romano e tantissimi altri monumenti. Quale ti interessa?',
            'rinascimento': 'Il Rinascimento italiano ha prodotto capolavori straordinari! Pensiamo al David di Michelangelo, alla Gioconda di Leonardo, o alla Cupola del Brunelleschi. Su quale vorresti saperne di più?',
            'museo': 'In Italia ci sono musei meravigliosi come gli Uffizi a Firenze, i Musei Vaticani a Roma, la Galleria Borghese e molti altri. Quale ti interessa?',
        };
        
        response = 'Interessante domanda! Posso aiutarti con informazioni su monumenti, opere d\'arte, musei e tanto altro. Vuoi essere più specifico?';
        
        const lowerMessage = userMessage.toLowerCase();
        for (const [key, value] of Object.entries(textResponses)) {
            if (lowerMessage.includes(key)) {
                response = value;
                break;
            }
        }
    }
    
    addBotMessage(response);

}

// PULSANTI NAVIGAZIONE
const backBtn = document.getElementById('backBtn');
const logoutBtn = document.getElementById('logoutBtn');

backBtn.addEventListener('click', () => {
    
    window.location.href = 'index.html';
});

logoutBtn.addEventListener('click', () => {
    // logout (implementare logica)
    if (confirm('Vuoi davvero uscire?')) {
        window.location.href = 'index.html';
    }
});