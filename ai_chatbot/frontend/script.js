document.addEventListener('DOMContentLoaded', () => {
    const chatIcon = document.getElementById('chat-icon');
    const chatWindow = document.getElementById('chat-window');
    const chatOverlay = document.getElementById('chat-overlay');
    const minimizeButton = document.getElementById('minimize-chat');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    // Toggle chat window
    chatIcon.addEventListener('click', () => {
        const isActive = chatWindow.classList.contains('active');
        if (isActive) {
            // Close chat
            chatWindow.classList.remove('active');
            chatOverlay.classList.remove('active');
        } else {
            // Open chat
            chatWindow.classList.add('active');
            chatOverlay.classList.add('active');
            userInput.focus();
        }
    });

    // Minimize chat window
    minimizeButton.addEventListener('click', (e) => {
        e.stopPropagation();
        chatWindow.classList.remove('active');
        chatOverlay.classList.remove('active');
    });

    // Close chat when clicking overlay
    chatOverlay.addEventListener('click', () => {
        chatWindow.classList.remove('active');
        chatOverlay.classList.remove('active');
    });

    // Auto-resize textarea
    userInput.addEventListener('input', () => {
        userInput.style.height = 'auto';
        const newHeight = Math.min(userInput.scrollHeight, 150);
        userInput.style.height = newHeight + 'px';
    });

    // Handle send button click
    sendButton.addEventListener('click', sendMessage);

    // Handle Enter key (without Shift)
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message to chat
        addMessage(message, 'user');
        userInput.value = '';
        userInput.style.height = 'auto';

        // Show typing indicator
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'typing-indicator';
        typingIndicator.innerHTML = '<span></span><span></span><span></span>';
        chatMessages.appendChild(typingIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Send message to backend
        fetch('http://localhost:5000/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message }),
        })
        .then(response => response.json())
        .then(data => {
            // Remove typing indicator
            chatMessages.removeChild(typingIndicator);
            
            // Add assistant response
            addMessage(data.response, 'assistant', data.sources);
        })
        .catch(error => {
            console.error('Error:', error);
            chatMessages.removeChild(typingIndicator);
            addMessage('Xin lỗi, có lỗi xảy ra. Vui lòng thử lại sau.', 'assistant');
        });
    }

    function addMessage(text, sender, sources = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        // Format text with proper line breaks and lists
        const formattedText = text
            .split('\n')
            .map(line => {
                // Handle numbered lists
                if (/^\d+\./.test(line)) {
                    return line;
                }
                // Handle bullet points
                if (line.trim().startsWith('-')) {
                    return '  ' + line;
                }
                return line;
            })
            .join('\n');
        
        // Process bold text markers (**text**)
        const processedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Use innerHTML to render HTML tags
        messageDiv.innerHTML = processedText;

        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'message-sources';
            sourcesDiv.textContent = 'Nguồn: ' + sources.join(', ');
            messageDiv.appendChild(sourcesDiv);
        }

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}); 