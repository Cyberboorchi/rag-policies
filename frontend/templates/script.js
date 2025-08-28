document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.getElementById('chat-box');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');

    // Enter товчлуур дээр дарж мессеж илгээх
    messageInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    // Илгээх товчлуур дээр дарж мессеж илгээх
    sendButton.addEventListener('click', sendMessage);

    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        // Хэрэглэгчийн мессежийг дэлгэцэнд харуулах
        addMessageToChat(message, 'user-message');
        messageInput.value = '';
        messageInput.disabled = true;

        try {
            // Сервер рүү хүсэлт илгээх
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });

            if (!response.ok) {
                throw new Error('Сүлжээний алдаа гарлаа. Дахин оролдоно уу.');
            }

            const data = await response.json();
            // Ботын хариултыг дэлгэцэнд харуулах
            addMessageToChat(data.reply, 'bot-message');
        } catch (error) {
            console.error('Алдаа:', error);
            addMessageToChat('Уучлаарай, хариулт өгөх боломжгүй байна. Дахин оролдоно уу.', 'bot-message');
        } finally {
            messageInput.disabled = false;
            messageInput.focus();
        }
    }

    function addMessageToChat(text, senderClass) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', senderClass);
        messageElement.textContent = text;
        chatBox.appendChild(messageElement);
        
        // Чат боксыг автоматаар доош гүйлгэх
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});