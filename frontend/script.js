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

                if (sender === 'assistant') {
                    // Xử lý đặc biệt cho assistant message
                    let formattedText = text
                        // Xử lý ** chỉ cho tiêu đề quan trọng
                        .replace(/\*\*(.*?)\*\*/g, '<strong class="title">$1</strong>')
                        // Giữ nguyên emoji
                        .replace(/([🏫📚✨📞🎯📋💡🔔🌟⭐📍📊💼🎓📝🏆🎉👥📱💻🔍📖✅])/g, '<span class="emoji">$1</span>')
                        // Xử lý bullet points với emoji
                        .replace(/^([•✓☑️▪️▫️◦])\s*(.*)$/gm, '<div class="bullet-point"><span class="bullet">$1</span> $2</div>')
                        // Xử lý numbered list  
                        .replace(/^(\d+\.\s*)(.*$)/gm, '<div class="numbered-item"><span class="number">$1</span>$2</div>')
                        // Xử lý phone/contact info
                        .replace(/(📞\s*.*?:\s*[\d\s\-\+\(\)]+)/g, '<div class="contact-info">$1</div>')
                        // Xử lý xuống dòng
                        .replace(/\n\n/g, '<br><br>')
                        .replace(/\n/g, '<br>');

                    messageDiv.innerHTML = formattedText;
                } else {
                    // User message giữ đơn giản
                    messageDiv.textContent = text;
                }

                // Thêm sources nếu có
                if (sources && sources.length > 0) {
                    const sourcesDiv = document.createElement('div');
                    sourcesDiv.className = 'message-sources';
                    sourcesDiv.innerHTML = `
                <div class="sources-header">
                    <i class="fas fa-book"></i> <span>Nguồn tham khảo:</span>
                </div>
                <div class="sources-list">
                    ${sources.map(source => `
                        <div class="source-item">
                            <i class="fas fa-link"></i>
                            <span>${source.title || source}</span>
                        </div>
                    `).join('')}
                </div>
            `;
            messageDiv.appendChild(sourcesDiv);
        }

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});