/**
 * Voice Entry Module for Warehouse Box Management
 * Uses Web Speech API for speech recognition and Gemini for parsing
 */

// State management
const state = {
    isListening: false,
    boxNumber: null,
    weight: null,
    contents: [], // Array of {product_type, quantity, lcd_size}
    recognition: null,
    finalTranscript: '',
    interimTranscript: ''
};

// Product types mapping (lowercase for matching)
const PRODUCT_TYPES = {
    'laptops': 'Laptops',
    'laptop': 'Laptops',
    'pcs': 'PCs',
    'pc': 'PCs',
    'computers': 'PCs',
    'computer': 'PCs',
    'desktops': 'PCs',
    'desktop': 'PCs',
    'lcds': 'LCDs',
    'lcd': 'LCDs',
    'monitors': 'LCDs',
    'monitor': 'LCDs',
    'screens': 'LCDs',
    'screen': 'LCDs',
    'displays': 'LCDs',
    'display': 'LCDs',
    'servers': 'Servers',
    'server': 'Servers',
    'switches': 'Switches',
    'switch': 'Switches',
    'network switches': 'Switches',
    'wires': 'Wires',
    'wire': 'Wires',
    'cables': 'Wires',
    'cable': 'Wires',
    'keyboards': 'Keyboards',
    'keyboard': 'Keyboards',
    'stands': 'Stands',
    'stand': 'Stands',
    'monitor stands': 'Stands'
};

// Number words mapping
const NUMBER_WORDS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
    'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30,
    'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
    'eighty': 80, 'ninety': 90, 'hundred': 100, 'thousand': 1000
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeSpeechRecognition);

function initializeSpeechRecognition() {
    // Check for browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        showError('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
        document.getElementById('micButton').disabled = true;
        document.getElementById('browserWarning').style.display = 'block';
        return;
    }

    state.recognition = new SpeechRecognition();
    state.recognition.continuous = true;
    state.recognition.interimResults = true;
    state.recognition.lang = 'en-US';

    state.recognition.onstart = () => {
        state.isListening = true;
        updateMicButton();
        updateStatus('Listening... Speak now');
    };

    state.recognition.onend = () => {
        state.isListening = false;
        updateMicButton();
        
        if (state.finalTranscript) {
            updateStatus('Processing...');
            processTranscript(state.finalTranscript);
        } else {
            updateStatus('Click to start speaking');
        }
    };

    state.recognition.onerror = (event) => {
        state.isListening = false;
        updateMicButton();
        
        if (event.error === 'not-allowed') {
            showError('Microphone access denied. Please allow microphone access in your browser settings.');
        } else if (event.error === 'no-speech') {
            updateStatus('No speech detected. Click to try again.');
        } else {
            showError(`Speech recognition error: ${event.error}`);
        }
    };

    state.recognition.onresult = (event) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                final += transcript;
            } else {
                interim += transcript;
            }
        }

        if (final) {
            state.finalTranscript += final;
        }
        state.interimTranscript = interim;

        updateTranscriptDisplay();
    };

    // Check if there's already some content (page refresh with state)
    updatePreview();
}

function toggleListening() {
    if (state.isListening) {
        stopListening();
    } else {
        startListening();
    }
}

function startListening() {
    if (!state.recognition) {
        showError('Speech recognition not initialized');
        return;
    }

    hideError();
    hideSuccess();
    state.finalTranscript = '';
    state.interimTranscript = '';
    
    try {
        state.recognition.start();
    } catch (e) {
        // Already started, ignore
    }
}

function stopListening() {
    if (state.recognition) {
        state.recognition.stop();
    }
}

function updateMicButton() {
    const button = document.getElementById('micButton');
    const icon = document.getElementById('micIcon');
    
    if (state.isListening) {
        button.classList.add('listening');
        button.classList.remove('processing');
        icon.textContent = '⏹';
    } else {
        button.classList.remove('listening', 'processing');
        icon.textContent = '🎤';
    }
}

function updateStatus(text, isListening = false) {
    const status = document.getElementById('micStatus');
    status.textContent = text;
    status.classList.toggle('listening', isListening || state.isListening);
}

function updateTranscriptDisplay() {
    const display = document.getElementById('transcriptText');
    
    if (state.finalTranscript || state.interimTranscript) {
        display.innerHTML = state.finalTranscript + 
            (state.interimTranscript ? `<span class="interim">${state.interimTranscript}</span>` : '');
    } else {
        display.textContent = 'Waiting for speech...';
    }
}

function processTranscript(transcript) {
    console.log('Processing transcript with LLM:', transcript);
    callLlmInterpreter(transcript);
}

async function callLlmInterpreter(transcript) {
    hideError();

    const payload = {
        transcript,
        current_box: {
            box_number: state.boxNumber,
            weight: state.weight,
            contents: state.contents
        }
    };

    try {
        const response = await fetch('/api/voice/interpret-box', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (!response.ok) {
            showError(result.error || 'Could not understand speech. Please try again.');
            updateStatus('Click to try speaking again');
            return;
        }

        state.boxNumber = result.box_number || state.boxNumber || null;
        state.weight = result.weight != null ? result.weight : state.weight;
        state.contents = result.contents || state.contents;

        if (result.notes && result.notes.length) {
            showSuccess(result.notes.join(' '));
        } else {
            hideSuccess();
        }

        updatePreview();
        updateStatus('Click microphone to add more, or confirm to save');
    } catch (error) {
        showError('Network/LLM error: ' + error.message);
        updateStatus('Voice understanding unavailable, you can still use manual entry');
    }
}

function updatePreview() {
    const card = document.getElementById('previewCard');
    const boxNumDisplay = document.getElementById('previewBoxNumber');
    const weightDisplay = document.getElementById('previewWeight');
    const contentsList = document.getElementById('contentsList');
    const confirmBtn = document.getElementById('btnConfirm');
    
    // Show preview card if we have any data
    const hasData = state.boxNumber || state.weight || state.contents.length > 0;
    card.style.display = hasData ? 'block' : 'none';
    
    // Update box number
    if (state.boxNumber) {
        boxNumDisplay.textContent = state.boxNumber;
    } else if (window.suggestedBoxNumber) {
        boxNumDisplay.innerHTML = `<span style="opacity: 0.5">${window.suggestedBoxNumber} (suggested)</span>`;
    } else {
        boxNumDisplay.textContent = '—';
    }
    
    // Update weight
    weightDisplay.textContent = state.weight ? `${state.weight} lbs` : '—';
    
    // Update contents list
    if (state.contents.length > 0) {
        contentsList.innerHTML = state.contents.map(item => {
            const name = item.lcd_size 
                ? `${item.product_type} (${item.lcd_size})`
                : item.product_type;
            return `
                <div class="content-item">
                    <span class="content-item-name">${name}</span>
                    <span class="content-item-qty">${item.quantity}</span>
                </div>
            `;
        }).join('');
    } else {
        contentsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📦</div>
                <div>No items added yet</div>
            </div>
        `;
    }
    
    // Enable confirm button if we have required data
    const canConfirm = (state.boxNumber || window.suggestedBoxNumber) && 
                       state.weight && 
                       state.contents.length > 0;
    confirmBtn.disabled = !canConfirm;
}

function addMore() {
    startListening();
}

function redoEntry() {
    state.boxNumber = null;
    state.weight = null;
    state.contents = [];
    state.finalTranscript = '';
    state.interimTranscript = '';
    
    document.getElementById('transcriptText').textContent = 'Waiting for speech...';
    hideError();
    hideSuccess();
    updatePreview();
    updateStatus('Click to start speaking');
}

async function confirmBox() {
    const confirmBtn = document.getElementById('btnConfirm');
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Saving...';
    
    const boxData = {
        box_number: state.boxNumber || window.suggestedBoxNumber,
        weight: state.weight,
        contents: state.contents
    };
    
    try {
        const response = await fetch('/api/boxes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(boxData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccess(`Box ${boxData.box_number} created successfully!`);
            
            // Update suggested box number
            const newSuggested = parseInt(boxData.box_number) + 1;
            window.suggestedBoxNumber = String(newSuggested);
            document.querySelector('.next-box-hint strong').textContent = newSuggested;
            
            // Reset for next entry
            setTimeout(() => {
                redoEntry();
            }, 1500);
        } else {
            showError(result.error || 'Failed to create box');
            confirmBtn.disabled = false;
            confirmBtn.textContent = '✓ Confirm & Save';
        }
    } catch (error) {
        showError('Network error: ' + error.message);
        confirmBtn.disabled = false;
        confirmBtn.textContent = '✓ Confirm & Save';
    }
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function hideError() {
    document.getElementById('errorMessage').style.display = 'none';
}

function showSuccess(message) {
    const successDiv = document.getElementById('successMessage');
    successDiv.textContent = message;
    successDiv.style.display = 'block';
}

function hideSuccess() {
    document.getElementById('successMessage').style.display = 'none';
}

