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

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const cameraBtn = document.getElementById('cameraBtn');
const cameraInput = document.getElementById('cameraInput');
const previewContainer = document.getElementById('previewContainer');
const previewImage = document.getElementById('previewImage');
const removeBtn = document.getElementById('removeBtn');
const inputContent = document.querySelector('.input-content');
let uploadedFile = null;

// previene comportamento default del browser SOLO per eventi drag
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
    }, false);
});

// highlight quando si trascina sopra
['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.classList.add('drag-over');
    }, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.classList.remove('drag-over');
    }, false);
});

// gestione drop
dropZone.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

// click su "Sfoglia File"
browseBtn.addEventListener('click', () => {
    fileInput.click();
});

// gestione selezione file
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// gestione file caricato
function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('Per favore carica solo immagini!');
        return;
    }
    uploadedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        inputContent.style.display = 'none';
        previewContainer.style.display = 'flex';
    };
    reader.readAsDataURL(file);
}

// gestione fotocamera
cameraBtn.addEventListener('click', () => {
    cameraInput.click();
});

cameraInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// rimuovi immagine
removeBtn.addEventListener('click', () => {
    uploadedFile = null;
    fileInput.value = '';
    previewImage.src = '';
    previewContainer.style.display = 'none';
    inputContent.style.display = 'flex';
});

// SUBMIT
const submitBtn = document.getElementById('submitBtn');
const textInput = document.getElementById('textInput');

textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.stopPropagation();
        submitBtn.click();
    }
});

submitBtn.addEventListener('click', async () => {
    const textValue = textInput.value.trim();

    if (!uploadedFile && !textValue) {
        alert('Per favore carica un\'immagine o scrivi una domanda!');
        return;
    }

    if (uploadedFile) {
        sessionStorage.setItem('inputType', 'image');
        if (textValue) sessionStorage.setItem('userMessage', textValue);
        const reader = new FileReader();
        reader.onload = (e) => {
            sessionStorage.setItem('uploadedImage', e.target.result);
            window.location.href = 'chat.html';
        };
        reader.readAsDataURL(uploadedFile);
    } else {
        sessionStorage.setItem('inputType', 'text');
        sessionStorage.setItem('userMessage', textValue);
        window.location.href = 'chat.html';
    }
});

// LOGIN
const loginBtn = document.getElementById('loginBtn');

loginBtn.addEventListener('click', () => {
    window.location.href = 'login.html';
});

// GALLERIA OPERE
const galleryBtn = document.getElementById('galleryBtn');
const galleryModal = document.getElementById('galleryModal');
const galleryModalClose = document.getElementById('galleryModalClose');
const galleryGrid = document.getElementById('galleryGrid');

galleryBtn.addEventListener('click', async () => {
    galleryModal.classList.add('active');
    galleryGrid.innerHTML = '<p class="gallery-loading">Caricamento opere...</p>';

    try {
        const response = await fetch('http://localhost:8000/api/artworks/');
        const artworks = await response.json();

        if (artworks.length === 0) {
            galleryGrid.innerHTML = '<p class="gallery-loading">Nessuna opera disponibile.</p>';
            return;
        }

        galleryGrid.innerHTML = artworks.map(artwork => `
            <div class="gallery-item" onclick="selectArtwork('${artwork.name.replace(/'/g, "\\'")}')">
                <img src="${artwork.images && artwork.images.length > 0 ? 'http://localhost:8000' + artwork.images[0].image : 'https://via.placeholder.com/160x120?text=No+Image'}" alt="${artwork.name}">
                <span class="gallery-item-name">${artwork.name}</span>
            </div>
        `).join('');
    } catch (error) {
        galleryGrid.innerHTML = '<p class="gallery-loading">Errore nel caricamento delle opere.</p>';
    }
});

galleryModalClose.addEventListener('click', () => {
    galleryModal.classList.remove('active');
});

galleryModal.addEventListener('click', (e) => {
    if (e.target === galleryModal) galleryModal.classList.remove('active');
});

function selectArtwork(artworkName) {
    galleryModal.classList.remove('active');
    sessionStorage.setItem('inputType', 'text');
    sessionStorage.setItem('userMessage', artworkName);
    sessionStorage.setItem('gallerySelected', 'true');
    window.location.href = 'chat.html';
}