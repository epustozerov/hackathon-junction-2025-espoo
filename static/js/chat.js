const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const micButton = document.getElementById('micButton');
const audioToggleButton = document.getElementById('audioToggleButton');

let audioOutputEnabled = true;

let recordingChunks = [];
let mediaRecorder = null;
let mediaStream = null;
let isRecording = false;

function addMessage(content, isUser) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const p = document.createElement('p');
    p.textContent = content;
    contentDiv.appendChild(p);
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    const now = new Date();
    timeDiv.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateProgress(completedSteps) {
    const progressSteps = Array.from(document.querySelectorAll('.progress-step'));
    
    progressSteps.forEach((step, index) => {
        const stepId = step.dataset.stepId;
        step.classList.remove('completed', 'active');
        
        if (completedSteps.includes(stepId)) {
            step.classList.add('completed');
        } else {
            const allPreviousCompleted = progressSteps
                .slice(0, index)
                .every(s => completedSteps.includes(s.dataset.stepId));
            
            if (allPreviousCompleted && index === completedSteps.length) {
                step.classList.add('active');
            }
        }
    });
    
    if (completedSteps.length > 0) {
        const firstIncompleteIndex = progressSteps.findIndex(
            step => !completedSteps.includes(step.dataset.stepId)
        );
        if (firstIncompleteIndex !== -1) {
            progressSteps[firstIncompleteIndex].classList.add('active');
        }
    } else {
        if (progressSteps.length > 0) {
            progressSteps[0].classList.add('active');
        }
    }
}

function updateTiersAndPoints(points, currentTierId, tiers) {
    const pointsValue = document.getElementById('pointsValue');
    if (pointsValue) {
        pointsValue.textContent = points || 0;
    }
    
    const tierItems = document.querySelectorAll('.tier-item');
    tierItems.forEach(item => {
        const tierId = item.dataset.tierId;
        item.classList.remove('unlocked', 'current');
        
        const tier = tiers.find(t => t.id === tierId);
        if (tier && points >= tier.points_required) {
            item.classList.add('unlocked');
            if (tierId === currentTierId) {
                item.classList.add('current');
            }
        }
    });
}

function validateEmail(email) {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailPattern.test(email);
}

function updateSendReportButton() {
    const sendReportButton = document.getElementById('sendReportButton');
    const emailInput = document.getElementById('reportEmailInput');
    
    if (sendReportButton && emailInput) {
        const email = emailInput.value.trim();
        const isValidEmail = validateEmail(email);
        
        if (isValidEmail) {
            sendReportButton.disabled = false;
            sendReportButton.title = 'Send current report to ' + email;
        } else {
            sendReportButton.disabled = true;
            sendReportButton.title = 'Please enter a valid email address';
        }
    }
}

async function sendReportManually() {
    const sendReportButton = document.getElementById('sendReportButton');
    const emailInput = document.getElementById('reportEmailInput');
    
    if (!sendReportButton || !emailInput || sendReportButton.disabled) {
        return;
    }
    
    const email = emailInput.value.trim();
    if (!validateEmail(email)) {
        addMessage('Please enter a valid email address.', false);
        return;
    }
    
    sendReportButton.disabled = true;
    const originalText = sendReportButton.querySelector('span').textContent;
    sendReportButton.querySelector('span').textContent = 'Sending...';
    
    try {
        const response = await fetch('/api/send-report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: email }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            addMessage('✓ Report has been sent to ' + email + '!', false);
            sendReportButton.querySelector('span').textContent = 'Report Sent!';
            setTimeout(() => {
                sendReportButton.querySelector('span').textContent = originalText;
                updateSendReportButton();
            }, 2000);
        } else {
            addMessage('Sorry, there was an error sending the report: ' + (data.error || 'Unknown error'), false);
            sendReportButton.querySelector('span').textContent = originalText;
            updateSendReportButton();
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('Sorry, there was an error connecting to the server.', false);
        sendReportButton.querySelector('span').textContent = originalText;
        updateSendReportButton();
    }
}

async function ensureStream() {
    if (mediaStream) return mediaStream;
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        return mediaStream;
    } catch (error) {
        console.error('Error accessing microphone:', error);
        addMessage('Microphone access denied. Please allow microphone access to use voice input.', false);
        throw error;
    }
}

function getSupportedMimeType() {
    const candidates = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/ogg'
    ];
    for (const type of candidates) {
        if (MediaRecorder.isTypeSupported(type)) return type;
    }
    return '';
}

function startRecording() {
    if (isRecording) return;
    recordingChunks = [];
    const mimeType = getSupportedMimeType();
    mediaRecorder = new MediaRecorder(mediaStream, mimeType ? { mimeType } : undefined);
    
    mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
            recordingChunks.push(e.data);
        }
    };
    
    mediaRecorder.onstop = async () => {
        if (!recordingChunks.length) return;
        
        const type = mediaRecorder.mimeType || 'audio/webm';
        const blob = new Blob(recordingChunks, { type });
        
        await transcribeAndSend(blob);
    };
    
    mediaRecorder.start();
    isRecording = true;
    micButton.classList.add('recording');
}

function stopRecording() {
    if (!isRecording) return;
    try {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
    } catch (error) {
        console.error('Error stopping recording:', error);
    }
    isRecording = false;
    micButton.classList.remove('recording');
}

async function transcribeAndSend(audioBlob) {
    micButton.disabled = true;
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    
    try {
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.text) {
            messageInput.value = data.text.trim();
            await sendMessage();
        } else {
            addMessage('Sorry, there was an error transcribing your audio.', false);
        }
    } catch (error) {
        console.error('Transcription error:', error);
        addMessage('Sorry, there was an error processing your audio.', false);
    } finally {
        micButton.disabled = false;
    }
}

function setupPressAndHold() {
    const start = async (e) => {
        e.preventDefault();
        try {
            await ensureStream();
            startRecording();
            window.addEventListener('pointerup', onPointerUpOnce, { once: true });
            window.addEventListener('pointercancel', onPointerUpOnce, { once: true });
            window.addEventListener('blur', onPointerUpOnce, { once: true });
        } catch (err) {
            micButton.classList.remove('recording');
            console.error('Error starting recording:', err);
        }
    };
    
    const end = () => {
        stopRecording();
    };
    
    const onPointerUpOnce = () => end();
    
    micButton.addEventListener('pointerdown', start);
}

function base64ToBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
}

async function playAudioFromTTS(text) {
    try {
        const response = await fetch('/api/tts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: text }),
        });
        
        const data = await response.json();
        
        if (response.ok && data.audio) {
            const audioBlob = base64ToBlob(data.audio, `audio/${data.format}`);
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            
            audio.play().catch(error => {
                console.error('Error playing audio:', error);
            });
            
            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
            };
        }
    } catch (error) {
        console.error('TTS error:', error);
    }
}

async function sendMessage() {
    const message = messageInput.value.trim();
    
    if (!message) {
        return;
    }
    
    addMessage(message, true);
    messageInput.value = '';
    sendButton.disabled = true;
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            setTimeout(() => {
                addMessage(data.response, false);
                updateProgress(data.completed_steps);
                updateTiersAndPoints(data.points, data.current_tier, data.tiers);
                
                if (data.form_data && data.form_data.email) {
                    const emailInput = document.getElementById('reportEmailInput');
                    if (emailInput && !emailInput.value.trim()) {
                        emailInput.value = data.form_data.email;
                    }
                }
                updateSendReportButton();
                
                if (data.report_sent) {
                    setTimeout(() => {
                        addMessage('✓ Report has been sent to your email address!', false);
                    }, 1000);
                }
                
                if (audioOutputEnabled) {
                    playAudioFromTTS(data.response);
                }
            }, 500);
        } else {
            addMessage('Sorry, there was an error processing your message.', false);
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('Sorry, there was an error connecting to the server.', false);
    } finally {
        sendButton.disabled = false;
        messageInput.focus();
    }
}

chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    sendMessage();
});

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

setupPressAndHold();

audioToggleButton.addEventListener('click', () => {
    audioOutputEnabled = !audioOutputEnabled;
    if (audioOutputEnabled) {
        audioToggleButton.classList.add('active');
        audioToggleButton.title = 'Audio output enabled - Click to disable';
    } else {
        audioToggleButton.classList.remove('active');
        audioToggleButton.title = 'Audio output disabled - Click to enable';
    }
});

audioToggleButton.classList.add('active');
audioToggleButton.title = 'Audio output enabled - Click to disable';

const themeToggleButton = document.getElementById('themeToggleButton');
const themeIcon = document.getElementById('themeIcon');
const htmlElement = document.documentElement;

function getThemeIcon(isDark) {
    if (isDark) {
        return `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>`;
    } else {
        return `<circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>`;
    }
}

function setTheme(theme) {
    if (theme === 'dark') {
        htmlElement.setAttribute('data-theme', 'dark');
        if (themeIcon) {
            themeIcon.innerHTML = getThemeIcon(true);
        }
        if (themeToggleButton) {
            themeToggleButton.title = 'Switch to light theme';
        }
        localStorage.setItem('theme', 'dark');
    } else {
        htmlElement.setAttribute('data-theme', 'light');
        if (themeIcon) {
            themeIcon.innerHTML = getThemeIcon(false);
        }
        if (themeToggleButton) {
            themeToggleButton.title = 'Switch to dark theme';
        }
        localStorage.setItem('theme', 'light');
    }
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
}

if (themeToggleButton) {
    themeToggleButton.addEventListener('click', () => {
        const currentTheme = htmlElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme);
    });
}

initTheme();
updateProgress([]);
updateTiersAndPoints(0, 'beginner', [
    {id: 'beginner', points_required: 0},
    {id: 'motivated_entrepreneur', points_required: 3},
    {id: 'growing_entrepreneur', points_required: 4},
    {id: 'experienced_business_professional', points_required: 6},
    {id: 'master_entrepreneur', points_required: 10}
]);
updateSendReportButton();

const sendReportButton = document.getElementById('sendReportButton');
const emailInput = document.getElementById('reportEmailInput');

if (sendReportButton) {
    sendReportButton.addEventListener('click', sendReportManually);
}

if (emailInput) {
    emailInput.addEventListener('input', updateSendReportButton);
    emailInput.addEventListener('blur', updateSendReportButton);
    emailInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !sendReportButton.disabled) {
            e.preventDefault();
            sendReportManually();
        }
    });
}

