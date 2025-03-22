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

    // Set model information if available
    fetch('/model-info')
        .then(response => response.json())
        .then(data => {
            if (data.model) {
                document.getElementById('model-info').textContent = data.model;
            }
        })
        .catch(() => {
            // If request fails, keep the default text
        });

    // Fetch tools info when page loads
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

// Add debugging to see when events are received
socket.on('reasoning_start', () => {
    console.log("Reasoning phase started");
    removeReasoningContainer();
    
    // Create a reasoning container
    const chatArea = document.getElementById('chat-area');
    const reasoningContainer = document.createElement('div');
    reasoningContainer.id = 'reasoning-container';
    reasoningContainer.className = 'reasoning-container';
    reasoningContainer.innerHTML = `
        <div class="reasoning-header">
            <span class="reasoning-icon">🧠</span>
            <span class="reasoning-title">Reasoning Phase</span>
        </div>
        <div class="reasoning-content" id="reasoning-content">
            <div class="thinking-indicator">Thinking...</div>
        </div>
    `;
    chatArea.appendChild(reasoningContainer);
    chatArea.scrollTop = chatArea.scrollHeight;
});

socket.on('reasoning', (data) => {
    console.log("Reasoning data received", data);
    const reasoningContent = document.getElementById('reasoning-content');
    if (reasoningContent) {
        reasoningContent.innerHTML = marked.parse(data.reasoning || "Thinking...");
        
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
    
    // Always create the execution container when execution phase starts
    createExecutionContainer();
});

socket.on('tool_call', (data) => {
    console.log("Tool call received", data);
    // Make sure execution container exists
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
            const args = data.args;
            argsHtml = Object.keys(args).map(key => {
                const value = typeof args[key] === 'string' && args[key].length > 50 
                    ? args[key].substring(0, 47) + '...' 
                    : args[key];
                return `<div class="tool-arg"><span class="arg-name">${key}:</span> <span class="arg-value">${value}</span></div>`;
            }).join('');
        }
        
        toolCallDiv.innerHTML = `
            <div class="tool-name">${data.name}</div>
            <div class="tool-args">${argsHtml}</div>
            <div class="tool-status">Running...</div>
        `;
        
        executionContent.appendChild(toolCallDiv);
        
        const chatArea = document.getElementById('chat-area');
        chatArea.scrollTop = chatArea.scrollHeight;
    }
});

// Ensure the execution container is created on execution_start
function createExecutionContainer() {
    console.log("Creating execution container");
    // Remove existing execution container if any
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
            <span class="execution-title">Execution Phase</span>
        </div>
        <div class="execution-content" id="execution-content"></div>
    `;
    chatArea.appendChild(executionContainer);
    chatArea.scrollTop = chatArea.scrollHeight;
}

socket.on('thinking', (data) => {
    if (data.content && data.content.trim()) {
        // Create execution container if it doesn't exist yet
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

socket.on('tool_result', (data) => {
    const executionContent = document.getElementById('execution-content');
    if (executionContent) {
        // Find the tool call div
        const toolCalls = executionContent.querySelectorAll('.tool-call');
        let toolCallDiv = null;
        
        // Find the most recent tool call div for this tool
        for (let i = toolCalls.length - 1; i >= 0; i--) {
            if (toolCalls[i].querySelector('.tool-name').textContent === data.name) {
                toolCallDiv = toolCalls[i];
                break;
            }
        }
        
        if (toolCallDiv) {
            const statusDiv = toolCallDiv.querySelector('.tool-status');
            statusDiv.textContent = `Completed in ${data.execution_time}s`;
            statusDiv.classList.add('success');
            
            const resultDiv = document.createElement('div');
            resultDiv.className = 'tool-result';
            
            if (typeof data.result === 'string' && (data.result.startsWith('{') || data.result.startsWith('['))) {
                try {
                    // Try to parse and format as JSON
                    const jsonObj = JSON.parse(data.result);
                    const jsonStr = JSON.stringify(jsonObj, null, 2);
                    resultDiv.innerHTML = `<pre><code class="language-json">${jsonStr}</code></pre>`;
                } catch (e) {
                    // If not valid JSON, show as regular text
                    resultDiv.textContent = data.result;
                }
            } else {
                resultDiv.textContent = data.result;
            }
            
            toolCallDiv.appendChild(resultDiv);
            
            // Apply syntax highlighting
            const codeBlock = resultDiv.querySelector('pre code');
            if (codeBlock) {
                hljs.highlightBlock(codeBlock);
            }
        } else {
            // Create a standalone result display if tool call div not found
            const resultDiv = document.createElement('div');
            resultDiv.className = 'standalone-result';
            resultDiv.innerHTML = `
                <div class="tool-name">${data.name} <span class="success">(${data.execution_time}s)</span></div>
                <div class="tool-result">${data.result}</div>
            `;
            executionContent.appendChild(resultDiv);
        }
        
        const chatArea = document.getElementById('chat-area');
        chatArea.scrollTop = chatArea.scrollHeight;
    }
});

socket.on('tool_error', (data) => {
    const executionContent = document.getElementById('execution-content');
    if (executionContent) {
        // Find the tool call div
        const toolCalls = executionContent.querySelectorAll('.tool-call');
        let toolCallDiv = null;
        
        // Find the most recent tool call div for this tool
        for (let i = toolCalls.length - 1; i >= 0; i--) {
            if (toolCalls[i].querySelector('.tool-name').textContent === data.name) {
                toolCallDiv = toolCalls[i];
                break;
            }
        }
        
        if (toolCallDiv) {
            const statusDiv = toolCallDiv.querySelector('.tool-status');
            statusDiv.textContent = 'Failed';
            statusDiv.classList.add('error');
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'tool-error';
            errorDiv.textContent = data.error;
            
            toolCallDiv.appendChild(errorDiv);
        } else {
            // Create a standalone error display if tool call div not found
            const errorDiv = document.createElement('div');
            errorDiv.className = 'standalone-error';
            errorDiv.innerHTML = `
                <div class="tool-name">${data.name} <span class="error">Failed</span></div>
                <div class="tool-error">${data.error}</div>
            `;
            executionContent.appendChild(errorDiv);
        }
        
        const chatArea = document.getElementById('chat-area');
        chatArea.scrollTop = chatArea.scrollHeight;
    }
});

socket.on('response', (data) => {
    // Enable input now that we have a response
    enableInput();
    
    // Remove typing indicator
    removeTypingIndicator();
    
    // Remove reasoning container
    removeReasoningContainer();
    
    if (data.error) {
        addMessageToChat('error', data.error);
    } else {
        addMessageToChat('assistant', data.message);
    }
});

function addMessageToChat(sender, message) {
    const chatArea = document.getElementById('chat-area');
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    
    // Style based on sender
    if (sender === 'user') {
        messageElement.className += ' user-message';
        messageElement.textContent = message;
    } else if (sender === 'error') {
        messageElement.className += ' error-message';
        messageElement.textContent = `Error: ${message}`;
    } else {
        // For assistant messages, render markdown
        messageElement.className += ' assistant-message';
        
        // Parse markdown and set inner HTML
        messageElement.innerHTML = marked.parse(message);
        
        // Apply syntax highlighting to code blocks
        messageElement.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightBlock(block);
        });
    }
    
    chatArea.appendChild(messageElement);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function addTypingIndicator() {
    removeTypingIndicator(); // Remove any existing indicator first
    
    const chatArea = document.getElementById('chat-area');
    const typingIndicator = document.createElement('div');
    typingIndicator.id = 'typing-indicator';
    typingIndicator.className = 'message assistant-message typing-indicator';
    
    // Create animated dots
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
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function removeReasoningContainer() {
    const reasoningContainer = document.getElementById('reasoning-container');
    if (reasoningContainer) {
        reasoningContainer.remove();
    }
    
    const executionContainer = document.getElementById('execution-container');
    if (executionContainer) {
        executionContainer.remove();
    }
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

// Fetch and display available tools
function fetchAvailableTools() {
    fetch('/tools-info')
        .then(response => response.json())
        .then(data => {
            const categoriesContainer = document.getElementById('tools-categories');
            if (!categoriesContainer) return;
            
            categoriesContainer.innerHTML = '';
            
            Object.keys(data.categories).forEach(category => {
                const tools = data.categories[category];
                
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
                categoriesContainer.appendChild(categoryDiv);
            });
            
            document.getElementById('tools-button-text').textContent = 
                `Available Tools (${data.total_tools})`;
        })
        .catch(error => {
            console.error('Error fetching tools info:', error);
        });
}

function toggleToolsPanel() {
    const panel = document.getElementById('tools-panel');
    panel.classList.toggle('hidden');
    
    const buttonText = document.getElementById('tools-button-text');
    if (panel.classList.contains('hidden')) {
        buttonText.textContent = buttonText.textContent.replace('Hide', 'Show');
    } else {
        buttonText.textContent = buttonText.textContent.replace('Show', 'Hide');
        // Only fetch tools if the panel is becoming visible
        fetchAvailableTools();
    }
}

function toggleCategoryTools(categoryElement) {
    const toolsList = categoryElement.nextElementSibling;
    toolsList.classList.toggle('visible');
    categoryElement.classList.toggle('expanded');
}
