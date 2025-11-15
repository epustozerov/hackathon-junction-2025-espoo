const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');

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
    const progressSteps = document.querySelectorAll('.progress-step');
    
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

updateProgress([]);

