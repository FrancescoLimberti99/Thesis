const API_BASE = 'http://localhost:8000/api';

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

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
    await fetch(`${API_BASE}/logout/`, {
        method: 'POST',
        credentials: 'include'
    });
    window.location.href = 'index.html';
});

// CARICA LISTA OPERE
async function loadArtworks() {
    try {
        const response = await fetch(`${API_BASE}/artworks/`, {
            credentials: 'include'
        });
        const artworks = await response.json();
        renderArtworks(artworks);
    } catch (error) {
        document.getElementById('artworkList').innerHTML =
            '<p class="loading-msg">Errore nel caricamento delle opere.</p>';
    }
}

function renderArtworks(artworks) {
    const list = document.getElementById('artworkList');

    if (artworks.length === 0) {
        list.innerHTML = '<p class="loading-msg">Nessuna opera presente</p>';
        return;
    }

    list.innerHTML = artworks.map(artwork => `
        <div class="artwork-item" id="artwork-${artwork.id}" onclick="openEditModal(${artwork.id})">
            <img src="${artwork.images && artwork.images.length > 0 ? 'http://localhost:8000' + artwork.images[0].image : 'https://via.placeholder.com/60'}" alt="${artwork.name}">
            <div class="artwork-item-info">
                <h4>${artwork.name}</h4>
                <p>${artwork.author} — ${artwork.period}</p>
            </div>
            <button class="delete-btn" onclick="event.stopPropagation(); deleteArtwork(${artwork.id})">Elimina</button>
        </div>
    `).join('');
}

// AGGIUNGI OPERA
document.getElementById('addArtworkBtn').addEventListener('click', async () => {
    const feedbackMsg = document.getElementById('feedbackMsg');

    const formData = new FormData();
    const images = document.getElementById('artworkImages').files;
    for (let i = 0; i < images.length; i++) {
        formData.append('images', images[i]);
    }
    formData.append('name', document.getElementById('artworkName').value.trim());
    formData.append('author', document.getElementById('artworkAuthor').value.trim());
    formData.append('period', document.getElementById('artworkPeriod').value.trim());
    formData.append('location', document.getElementById('artworkLocation').value.trim());
    formData.append('style', document.getElementById('artworkStyle').value.trim());
    formData.append('context', document.getElementById('artworkContext').value.trim());
    formData.append('aliases', document.getElementById('artworkAliases').value.trim());

    if (!formData.get('name') || !formData.get('author')) {
        feedbackMsg.className = 'feedback-msg error';
        feedbackMsg.textContent = 'Nome e autore sono obbligatori';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/artworks/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: formData,
            credentials: 'include'
        });

        if (response.ok) {
            feedbackMsg.className = 'feedback-msg success';
            feedbackMsg.textContent = 'Opera aggiunta con successo!';
            loadArtworks();

            document.getElementById('artworkImages').value = '';
            document.getElementById('artworkName').value = '';
            document.getElementById('artworkAuthor').value = '';
            document.getElementById('artworkPeriod').value = '';
            document.getElementById('artworkLocation').value = '';
            document.getElementById('artworkStyle').value = '';
            document.getElementById('artworkContext').value = '';
            document.getElementById('artworkAliases').value = '';
        } else {
            feedbackMsg.className = 'feedback-msg error';
            feedbackMsg.textContent = 'Errore nell\'aggiunta dell\'opera';
        }
    } catch (error) {
        feedbackMsg.className = 'feedback-msg error';
        feedbackMsg.textContent = 'Errore di connessione. Il server è avviato?';
    }
});

// ELIMINA OPERA
async function deleteArtwork(id) {
    if (!confirm('Sei sicuro di voler eliminare questa opera?')) return;

    try {
        const response = await fetch(`${API_BASE}/artworks/${id}/`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            credentials: 'include'
        });

        if (response.ok) {
            document.getElementById(`artwork-${id}`).remove();
        }
    } catch (error) {
        alert('Errore di connessione. Il server è avviato?');
    }
}

// MODAL MODIFICA OPERA
let currentEditId = null;

async function openEditModal(id) {
    const r = await fetch(`${API_BASE}/artworks/${id}/`, { credentials: 'include' });
    const artwork = await r.json();

    currentEditId = id;
    document.getElementById('editName').value = artwork.name;
    document.getElementById('editAuthor').value = artwork.author;
    document.getElementById('editPeriod').value = artwork.period;
    document.getElementById('editLocation').value = artwork.location;
    document.getElementById('editStyle').value = artwork.style;
    document.getElementById('editContext').value = artwork.context;
    document.getElementById('editAliases').value = artwork.aliases || '';
    document.getElementById('editImages').value = '';
    document.getElementById('editFeedbackMsg').textContent = '';

    const imagesContainer = document.getElementById('editCurrentImages');
    if (artwork.images && artwork.images.length > 0) {
        imagesContainer.innerHTML = artwork.images.map(img =>
            `<img src="http://localhost:8000${img.image}" style="width:60px;height:60px;object-fit:cover;margin:4px;border-radius:4px;">`
        ).join('');
    } else {
        imagesContainer.innerHTML = '<small>Nessuna immagine</small>';
    }

    document.getElementById('modalOverlay').classList.add('active');
}

function closeEditModal() {
    document.getElementById('modalOverlay').classList.remove('active');
    ['editName', 'editAuthor', 'editPeriod', 'editLocation', 'editStyle', 'editContext', 'editAliases'].forEach(id => {
        document.getElementById(id).value = '';
    });
    document.getElementById('editImages').value = '';
    document.getElementById('editCurrentImages').innerHTML = '';
    document.getElementById('editFeedbackMsg').textContent = '';
}

document.getElementById('cancelEditBtn').addEventListener('click', closeEditModal);

document.getElementById('modalOverlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('modalOverlay')) closeEditModal();
});

document.getElementById('saveEditBtn').addEventListener('click', async () => {
    const feedbackMsg = document.getElementById('editFeedbackMsg');
    const formData = new FormData();

    const images = document.getElementById('editImages').files;
    for (let i = 0; i < images.length; i++) {
        formData.append('images', images[i]);
    }
    formData.append('name', document.getElementById('editName').value.trim());
    formData.append('author', document.getElementById('editAuthor').value.trim());
    formData.append('period', document.getElementById('editPeriod').value.trim());
    formData.append('location', document.getElementById('editLocation').value.trim());
    formData.append('style', document.getElementById('editStyle').value.trim());
    formData.append('context', document.getElementById('editContext').value.trim());
    formData.append('aliases', document.getElementById('editAliases').value.trim());

    try {
        const response = await fetch(`${API_BASE}/artworks/${currentEditId}/`, {
            method: 'PUT',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: formData,
            credentials: 'include'
        });

        if (response.ok) {
            feedbackMsg.className = 'feedback-msg success';
            feedbackMsg.textContent = 'Opera modificata con successo!';
            loadArtworks();
            setTimeout(closeEditModal, 1000);
        } else {
            feedbackMsg.className = 'feedback-msg error';
            feedbackMsg.textContent = 'Errore nella modifica.';
        }
    } catch (error) {
        feedbackMsg.className = 'feedback-msg error';
        feedbackMsg.textContent = 'Errore di connessione.';
    }
});

// AVVIO
loadArtworks();