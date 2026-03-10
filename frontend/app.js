// SLIDESHOW AUTOMATICO
let currentSlide = 0;
const slides = document.querySelectorAll('.slide');

function showSlide(index) {
    
    slides.forEach(slide => slide.classList.remove('active'));
    
    //attivazione slide corrente
    slides[index].classList.add('active');
}

function nextSlide() {
    currentSlide = (currentSlide + 1) % slides.length;
    showSlide(currentSlide);
}

setInterval(nextSlide, 10000); //intervallo rotazione slides

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

// previene comportamento default del browser
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

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
    // verifica che sia immagine
    if (!file.type.startsWith('image/')) {
        alert('Per favore carica solo immagini!');
        return;
    }
    
    uploadedFile = file;
    
    // mostra preview
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        inputContent.style.display = 'none';
        previewContainer.style.display = 'block';
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

submitBtn.addEventListener('click', async () => {
    const textValue = textInput.value.trim();
    
    if (!uploadedFile && !textValue) {
        alert('Per favore carica un\'immagine o scrivi una domanda!');
        return;
    }
    
    if (uploadedFile) {
        sessionStorage.setItem('inputType', 'image');
        if (textValue) sessionStorage.setItem('userMessage', textValue);
        // salva il file temporaneamente come base64
        const reader = new FileReader();
        reader.onload = (e) => {
            sessionStorage.setItem('uploadedImage', e.target.result);
            window.location.href = 'chat.html';
        };
        reader.readAsDataURL(uploadedFile);
    } else {
        sessionStorage.setItem('inputType', 'text');
        sessionStorage.setItem('userMessage', textValue);
        console.log('Salvato:', sessionStorage.getItem('inputType'), sessionStorage.getItem('userMessage'));
        window.location.href = 'chat.html';
    }
});

// LOGIN
const loginBtn = document.getElementById('loginBtn');

loginBtn.addEventListener('click', () => {
    window.location.href = 'login.html';
});