const socket = io();

// Initialize the chat
document.addEventListener('DOMContentLoaded', () => {
    // Setup UI event handlers
    document.getElementById('send-button').addEventListener('click', sendMessage);
    document.getElementById('user-input').addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    // Fetch initial model info
    fetch('/model-info')
        .then(response => response.json())
        .then(data => {
            if (data.name && data.model) {
                document.getElementById('model-info').textContent = `${data.name} (${data.model})`;
            }
        })
        .catch(console.error);

    // Fetch tools info
    fetchAvailableTools();
});

function sendMessage() {
    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();
    if (message) {
        addMessageToChat('user', message);
        socket.emit('send_message', { message });
        userInput.value = '';
        
        // Disable input while processing
        disableInput();
        
        // Show typing indicator
        addTypingIndicator();
    }
}

socket.on('connected', (data) => {
    console.log('Connected to server', data);
    if (data.name && data.model) {
        document.getElementById('model-info').textContent = `${data.name} (${data.model})`;
    }
});

socket.on('reasoning_start', () => {
    console.log("Reasoning phase started");
    removeReasoningContainer();
    
    const chatArea = document.getElementById('chat-area');
    const reasoningContainer = document.createElement('div');
    reasoningContainer.id = 'reasoning-container';
    reasoningContainer.className = 'reasoning-container';
    reasoningContainer.innerHTML = `
        <div class="reasoning-header">
            <span class="reasoning-icon">🧠</span>
            <span class="reasoning-title">Understanding & Planning</span>
        </div>
        <div class="reasoning-content" id="reasoning-content">
            <div class="thinking-indicator">Analyzing request...</div>
        </div>
    `;
    chatArea.appendChild(reasoningContainer);
    chatArea.scrollTop = chatArea.scrollHeight;
});

socket.on('reasoning', (data) => {
    console.log("Reasoning received", data);
    const reasoningContent = document.getElementById('reasoning-content');
    if (reasoningContent && data.content) {
        reasoningContent.innerHTML = marked.parse(data.content);
        
        // Remove thinking indicator if it exists
        const thinkingIndicator = reasoningContent.querySelector('.thinking-indicator');
        if (thinkingIndicator) {
            thinkingIndicator.remove();
        }
        
        // Apply syntax highlighting
        reasoningContent.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightBlock(block);
        });
        
        const chatArea = document.getElementById('chat-area');
        chatArea.scrollTop = chatArea.scrollHeight;
    }
});

socket.on('execution_start', () => {
    console.log("Execution phase started");
    removeTypingIndicator();
    createExecutionContainer();
});

function createExecutionContainer() {
    const existingContainer = document.getElementById('execution-container');
    if (existingContainer) {
        existingContainer.remove();
    }
    
    const chatArea = document.getElementById('chat-area');
    const executionContainer = document.createElement('div');
    executionContainer.id = 'execution-container';
    executionContainer.className = 'execution-container';
    executionContainer.innerHTML = `
        <div class="execution-header">
            <span class="execution-icon">⚙️</span>
            <span class="execution-title">Working on Solution</span>
        </div>
        <div class="execution-content" id="execution-content"></div>
    `;
    chatArea.appendChild(executionContainer);
    chatArea.scrollTop = chatArea.scrollHeight;
}

socket.on('thinking', (data) => {
    if (data.content && data.content.trim()) {
        if (!document.getElementById('execution-container')) {
            createExecutionContainer();
        }
        
        const executionContent = document.getElementById('execution-content');
        if (executionContent) {
            const thinkingDiv = document.createElement('div');
            thinkingDiv.className = 'assistant-thinking';
            thinkingDiv.innerHTML = marked.parse(data.content);
            executionContent.appendChild(thinkingDiv);
            
            const chatArea = document.getElementById('chat-area');
            chatArea.scrollTop = chatArea.scrollHeight;
        }
    }
});

socket.on('tool_call', (data) => {
    console.log("Tool call", data);
    if (!document.getElementById('execution-container')) {
        createExecutionContainer();
    }
    
    const executionContent = document.getElementById('execution-content');
    if (executionContent) {
        const toolCallDiv = document.createElement('div');
        toolCallDiv.className = 'tool-call';
        toolCallDiv.id = `tool-call-${data.name}-${Date.now()}`;
        
        let argsHtml = '';
        if (data.args) {
            argsHtml = Object.entries(data.args)
                .map(([key, value]) => {
                    const displayValue = typeof value === 'string' && value.length > 50 
                        ? value.substring(0, 47) + '...' 
                        : JSON.stringify(value);
                    return `<div class="tool-arg"><span class="arg-name">${key}:</span> <span class="arg-value">${displayValue}</span></div>`;
                }).join('');
        }
        
        toolCallDiv.innerHTML = `
            <div class="tool-name">${data.name}</div>
            <div class="tool-args">${argsHtml}</div>
            <div class="tool-status">Running...</div>
        `;
        
        executionContent.appendChild(toolCallDiv);
        executionContent.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
});

socket.on('tool_result', (data) => {
    const executionContent = document.getElementById('execution-content');
    if (executionContent) {
        // Find the most recent matching tool call
        const toolCalls = Array.from(executionContent.querySelectorAll('.tool-call'));
        const toolCallDiv = toolCalls.reverse()
            .find(div => div.querySelector('.tool-name').textContent === data.name);
        
        if (toolCallDiv) {
            const statusDiv = toolCallDiv.querySelector('.tool-status');
            statusDiv.textContent = `Completed in ${data.execution_time}s`;
            statusDiv.classList.add('success');
            
            if (data.result) {
                const resultDiv = document.createElement('div');
                resultDiv.className = 'tool-result';
                
                // Try to parse and format as JSON if applicable
                try {
                    if (typeof data.result === 'string' && 
                        (data.result.startsWith('{') || data.result.startsWith('['))) {
                        const jsonObj = JSON.parse(data.result);
                        resultDiv.innerHTML = `<pre><code class="language-json">${JSON.stringify(jsonObj, null, 2)}</code></pre>`;
                    } else {
                        resultDiv.textContent = data.result;
                    }
                } catch (e) {
                    resultDiv.textContent = data.result;
                }
                
                toolCallDiv.appendChild(resultDiv);
                
                // Apply syntax highlighting
                const codeBlock = resultDiv.querySelector('pre code');
                if (codeBlock) {
                    hljs.highlightBlock(codeBlock);
                }
            }
            
            toolCallDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
});

socket.on('tool_error', (data) => {
    const executionContent = document.getElementById('execution-content');
    if (executionContent) {
        const toolCalls = Array.from(executionContent.querySelectorAll('.tool-call'));
        const toolCallDiv = toolCalls.reverse()
            .find(div => div.querySelector('.tool-name').textContent === data.name);
        
        if (toolCallDiv) {
            const statusDiv = toolCallDiv.querySelector('.tool-status');
            statusDiv.textContent = 'Failed';
            statusDiv.classList.add('error');
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'tool-error';
            errorDiv.textContent = data.error;
            
            toolCallDiv.appendChild(errorDiv);
            toolCallDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
});

socket.on('error', (data) => {
    console.error('Error:', data);
    enableInput();
    removeTypingIndicator();
    addMessageToChat('error', data.message || 'An error occurred');
});

socket.on('response', (data) => {
    enableInput();
    removeTypingIndicator();
    
    if (data.error) {
        addMessageToChat('error', data.error);
    } else {
        // Create response with metadata
        const responseData = {
            message: data.message,
            metadata: {
                reasoning: data.metadata?.reasoning,
                toolCallsCount: data.metadata?.tool_calls_count
            }
        };
        addMessageToChat('assistant', responseData);
    }
});

function addMessageToChat(sender, data) {
    const chatArea = document.getElementById('chat-area');
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    
    if (sender === 'user') {
        messageElement.className += ' user-message';
        messageElement.textContent = data;
    } else if (sender === 'error') {
        messageElement.className += ' error-message';
        messageElement.textContent = `Error: ${data}`;
    } else {
        messageElement.className += ' assistant-message';
        const responseContainer = document.createElement('div');
        responseContainer.className = 'assistant-response-container';
        
        // Add execution section if there were tool calls
        const executionContainer = document.getElementById('execution-container');
        if (executionContainer) {
            const executionContent = executionContainer.querySelector('.execution-content').innerHTML;
            if (executionContent) {
                const executionSection = createCollapsibleSection(
                    `⚙️ Actions Used (${data.metadata?.toolCallsCount || 0})`,
                    executionContent,
                    'execution-section'
                );
                responseContainer.appendChild(executionSection);
            }
            executionContainer.remove();
        }
        
        // Add the main message content
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = marked.parse(data.message);
        responseContainer.appendChild(messageContent);
        
        messageElement.appendChild(responseContainer);
        
        // Apply syntax highlighting
        messageElement.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightBlock(block);
        });
        
        removeReasoningContainer();
    }
    
    chatArea.appendChild(messageElement);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function createCollapsibleSection(title, content, className) {
    const section = document.createElement('div');
    section.className = className;
    section.innerHTML = `
        <div class="collapsible" onclick="toggleCollapsible(this)">
            <span class="section-title">${title}</span>
            <span class="toggle-icon">▶</span>
        </div>
        <div class="collapsible-content" style="display: none;">
            ${content}
        </div>
    `;
    return section;
}

function toggleCollapsible(header) {
    const content = header.nextElementSibling;
    const isHidden = content.style.display === 'none';
    content.style.display = isHidden ? 'block' : 'none';
    const icon = header.querySelector('.toggle-icon');
    icon.textContent = isHidden ? '▼' : '▶';
}


function addTypingIndicator() {
    removeTypingIndicator();
    const chatArea = document.getElementById('chat-area');
    const typingIndicator = document.createElement('div');
    typingIndicator.id = 'typing-indicator';
    typingIndicator.className = 'message assistant-message typing-indicator';
    typingIndicator.innerHTML = `
        <span class="dot-typing">Assistant is thinking</span>
        <span class="dot">.</span>
        <span class="dot">.</span>
        <span class="dot">.</span>
    `;
    chatArea.appendChild(typingIndicator);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

function removeReasoningContainer() {
    const container = document.getElementById('reasoning-container');
    if (container) container.remove();
}

function disableInput() {
    document.getElementById('user-input').disabled = true;
    document.getElementById('send-button').disabled = true;
}

function enableInput() {
    document.getElementById('user-input').disabled = false;
    document.getElementById('send-button').disabled = false;
    document.getElementById('user-input').focus();
}

function fetchAvailableTools() {
    fetch('/tools-info')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('tools-categories');
            if (!container) return;
            
            container.innerHTML = '';
            Object.entries(data.categories).forEach(([category, tools]) => {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'tool-category';
                
                const categoryName = document.createElement('div');
                categoryName.className = 'category-name';
                categoryName.textContent = category.replace(/_/g, ' ');
                categoryName.onclick = () => toggleCategoryTools(categoryName);
                
                const toolsList = document.createElement('div');
                toolsList.className = 'category-tools';
                
                tools.forEach(tool => {
                    const toolItem = document.createElement('div');
                    toolItem.className = 'tool-item';
                    toolItem.textContent = tool;
                    toolsList.appendChild(toolItem);
                });
                
                categoryDiv.appendChild(categoryName);
                categoryDiv.appendChild(toolsList);
                container.appendChild(categoryDiv);
            });
            
            document.getElementById('tools-button-text').textContent = 
                `Available Tools (${data.total_tools})`;
        })
        .catch(console.error);
}

function toggleToolsPanel() {
    const panel = document.getElementById('tools-panel');
    panel.classList.toggle('hidden');
    
    const buttonText = document.getElementById('tools-button-text');
    if (panel.classList.contains('hidden')) {
        buttonText.textContent = buttonText.textContent.replace('Hide', 'Show');
    } else {
        buttonText.textContent = buttonText.textContent.replace('Show', 'Hide');
        fetchAvailableTools();
    }
}

function toggleCategoryTools(categoryElement) {
    const toolsList = categoryElement.nextElementSibling;
    toolsList.classList.toggle('visible');
    categoryElement.classList.toggle('expanded');
}
