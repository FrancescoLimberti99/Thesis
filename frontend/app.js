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

// DRAG AND DROP
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
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
    
    // gestione 2 casi: immagine o testo
    if (uploadedFile) {
        // CASO 1: immagine
        const reader = new FileReader();
        reader.onload = (e) => {
            localStorage.setItem('uploadedImage', e.target.result);
            localStorage.setItem('inputType', 'image'); // flag per distinguere
            
            // se contiene anche testo va salvato
            if (textValue) {
                localStorage.setItem('userMessage', textValue);
            }
            
            window.location.href = 'chat.html';
        };
        reader.readAsDataURL(uploadedFile);
    } else {
        // CASO 2: solo testo
        localStorage.setItem('userMessage', textValue);
        localStorage.setItem('inputType', 'text'); // flag per distinguere
        window.location.href = 'chat.html';
    }
});

// LOGIN
const loginBtn = document.getElementById('loginBtn');

loginBtn.addEventListener('click', () => {
    //TODO implementa login
    alert('Funzionalità login in sviluppo!');
    //window.location.href = '/login';
});