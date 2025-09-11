interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  streaming?: boolean;
}

interface PebbleMindClient {
  messages: Message[];
  isConnected: boolean;
  isLoading: boolean;
  currentModel: string;
  apiBaseUrl: string;
}

class PebbleMindDesktopApp {
  private client: PebbleMindClient;
  private elements: {
    statusDot: HTMLElement | null;
    statusText: HTMLElement | null;
    modelSelector: HTMLSelectElement | null;
    welcomeScreen: HTMLElement | null;
    messagesContainer: HTMLElement | null;
    loadingIndicator: HTMLElement | null;
    messageInput: HTMLTextAreaElement | null;
    sendButton: HTMLButtonElement | null;
  };

  constructor() {
    this.client = {
      messages: [],
      isConnected: false,
      isLoading: false,
      currentModel: '3b',
      apiBaseUrl: 'http://localhost:8000'
    };

    this.elements = {
      statusDot: null,
      statusText: null,
      modelSelector: null,
      welcomeScreen: null,
      messagesContainer: null,
      loadingIndicator: null,
      messageInput: null,
      sendButton: null
    };

    this.initializeElements();
    this.setupEventListeners();
    this.checkConnection();
  }

  private initializeElements(): void {
    this.elements.statusDot = document.getElementById('statusDot');
    this.elements.statusText = document.getElementById('statusText');
    this.elements.modelSelector = document.getElementById('modelSelector') as HTMLSelectElement;
    this.elements.welcomeScreen = document.getElementById('welcomeScreen');
    this.elements.messagesContainer = document.getElementById('messages');
    this.elements.loadingIndicator = document.getElementById('loadingIndicator');
    this.elements.messageInput = document.getElementById('messageInput') as HTMLTextAreaElement;
    this.elements.sendButton = document.getElementById('sendButton') as HTMLButtonElement;
  }

  private setupEventListeners(): void {
    // Send button click
    this.elements.sendButton?.addEventListener('click', () => this.sendMessage());

    // Enter key to send (Ctrl+Enter or just Enter)
    this.elements.messageInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Model selector change
    this.elements.modelSelector?.addEventListener('change', (e) => {
      const target = e.target as HTMLSelectElement;
      this.switchModel(target.value);
    });

    // Auto-resize textarea
    this.elements.messageInput?.addEventListener('input', (e) => {
      const target = e.target as HTMLTextAreaElement;
      target.style.height = 'auto';
      target.style.height = Math.min(target.scrollHeight, 128) + 'px';
    });

    // Connection retry on click
    this.elements.statusDot?.addEventListener('click', () => {
      if (!this.client.isConnected) {
        this.checkConnection();
      }
    });
  }

  private async checkConnection(): Promise<void> {
    this.updateConnectionStatus('connecting', 'Connecting...');
    
    try {
      const response = await fetch(`${this.client.apiBaseUrl}/health`);
      if (response.ok) {
        this.client.isConnected = true;
        this.updateConnectionStatus('connected', 'Connected');
        
        // Check model status
        await this.checkModelStatus();
      } else {
        throw new Error('API not responding');
      }
    } catch (error) {
      this.client.isConnected = false;
      this.updateConnectionStatus('disconnected', 'Disconnected - Click to retry');
      console.error('Connection failed:', error);
      
      // Show connection error
      this.showConnectionError();
      
      // Retry after 5 seconds
      setTimeout(() => this.checkConnection(), 5000);
    }
  }

  private async checkModelStatus(): Promise<void> {
    try {
      // This would call a PebbleMind status endpoint
      // For now, we'll simulate this
      console.log('Checking model status...');
    } catch (error) {
      console.error('Failed to check model status:', error);
    }
  }

  private updateConnectionStatus(status: 'connected' | 'connecting' | 'disconnected', text: string): void {
    if (this.elements.statusDot) {
      this.elements.statusDot.className = `status-dot ${status}`;
    }
    if (this.elements.statusText) {
      this.elements.statusText.textContent = text;
    }
  }

  private showConnectionError(): void {
    if (!this.elements.messagesContainer) return;

    const errorElement = document.createElement('div');
    errorElement.className = 'connection-status';
    errorElement.innerHTML = `
      <div style="color: var(--error-color);">⚠️</div>
      <div>
        <strong>Unable to connect to PebbleMind API</strong><br>
        <small>Make sure the PebbleMind server is running on ${this.client.apiBaseUrl}</small>
      </div>
    `;

    this.elements.messagesContainer.appendChild(errorElement);
    this.scrollToBottom();
  }

  private async switchModel(modelSize: string): Promise<void> {
    if (!this.client.isConnected || this.client.isLoading) {
      return;
    }

    this.client.currentModel = modelSize;
    this.updateConnectionStatus('connecting', `Switching to ${modelSize.toUpperCase()} model...`);
    
    try {
      // This would call the PebbleMind model switch API
      // For demo purposes, we'll simulate this
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      this.updateConnectionStatus('connected', `${modelSize.toUpperCase()} model active`);
      
      // Add system message
      this.addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `Switched to ${modelSize.toUpperCase()} model. ${this.getModelDescription(modelSize)}`,
        timestamp: new Date()
      });
      
    } catch (error) {
      this.updateConnectionStatus('connected', 'Connected');
      console.error('Model switch failed:', error);
      
      // Reset selector
      if (this.elements.modelSelector) {
        this.elements.modelSelector.value = this.client.currentModel;
      }
    }
  }

  private getModelDescription(modelSize: string): string {
    switch (modelSize) {
      case '1.5b':
        return 'Ultra-light model for fastest responses.';
      case '3b':
        return 'Balanced model for optimal quality and speed.';
      case '7b':
        return 'High-quality model with advanced reasoning.';
      default:
        return '';
    }
  }

  private async sendMessage(): Promise<void> {
    const input = this.elements.messageInput;
    if (!input || !input.value.trim() || this.client.isLoading || !this.client.isConnected) {
      return;
    }

    const messageText = input.value.trim();
    input.value = '';
    input.style.height = 'auto';

    // Hide welcome screen and show messages
    this.showMessages();

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      timestamp: new Date()
    };
    this.addMessage(userMessage);

    // Start loading
    this.setLoading(true);

    try {
      // Send to PebbleMind API with streaming
      await this.sendStreamingRequest(messageText);
    } catch (error) {
      console.error('Message failed:', error);
      this.addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your message. Please try again.',
        timestamp: new Date()
      });
    } finally {
      this.setLoading(false);
    }
  }

  private async sendStreamingRequest(message: string): Promise<void> {
    // Create assistant message for streaming
    const assistantMessage: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true
    };

    const messageElement = this.addMessage(assistantMessage);
    const contentElement = messageElement.querySelector('.message-content') as HTMLElement;

    try {
      const response = await fetch(`${this.client.apiBaseUrl}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'pebblemind-chat',
          messages: [
            { role: 'user', content: message }
          ],
          stream: true,
          temperature: 0.7
        })
      });

      if (!response.ok) {
        throw new Error(`API responded with status ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response stream available');
      }

      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        // Process complete lines
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            
            if (data === '[DONE]') {
              break;
            }
            
            try {
              const json = JSON.parse(data);
              const delta = json.choices?.[0]?.delta?.content;
              
              if (delta) {
                assistantMessage.content += delta;
                contentElement.textContent = assistantMessage.content;
                this.scrollToBottom();
              }
            } catch (e) {
              // Ignore JSON parse errors for malformed chunks
              console.warn('Failed to parse streaming chunk:', data);
            }
          }
        }
      }
      
      // Finalize message
      assistantMessage.streaming = false;
      messageElement.classList.remove('streaming');
      
      // Remove streaming cursor
      const cursor = messageElement.querySelector('.streaming-cursor');
      if (cursor) {
        cursor.remove();
      }
      
    } catch (error) {
      console.error('Streaming request failed:', error);
      
      // Fallback to non-streaming for demo
      assistantMessage.content = this.generateDemoResponse(message);
      assistantMessage.streaming = false;
      messageElement.classList.remove('streaming');
      contentElement.textContent = assistantMessage.content;
      
      // Remove streaming cursor
      const cursor = messageElement.querySelector('.streaming-cursor');
      if (cursor) {
        cursor.remove();
      }
    }
  }

  private generateDemoResponse(message: string): string {
    // Demo responses for when API is not available
    const responses = [
      `I understand you're asking about "${message}". This is a demo response since the PebbleMind API server is not running. To get real responses, please start the PebbleMind server with: pebblemind serve`,
      
      `Thank you for your message: "${message}". PebbleMind is designed to provide intelligent responses using local AI models. Start the API server to experience real-time AI conversation.`,
      
      `Your query "${message}" would normally be processed by one of our Qwen2.5 models (1.5B, 3B, or 7B). Please run 'pebblemind serve' in your terminal to enable full functionality.`
    ];
    
    return responses[Math.floor(Math.random() * responses.length)];
  }

  private addMessage(message: Message): HTMLElement {
    this.client.messages.push(message);
    
    if (!this.elements.messagesContainer) {
      throw new Error('Messages container not found');
    }

    const messageElement = document.createElement('div');
    messageElement.className = `message ${message.role}${message.streaming ? ' streaming' : ''}`;
    messageElement.dataset.messageId = message.id;

    const contentElement = document.createElement('div');
    contentElement.className = 'message-content';
    contentElement.textContent = message.content;

    const metaElement = document.createElement('div');
    metaElement.className = 'message-meta';
    metaElement.textContent = message.timestamp.toLocaleTimeString();

    messageElement.appendChild(contentElement);
    messageElement.appendChild(metaElement);

    // Add streaming cursor for assistant messages
    if (message.streaming && message.role === 'assistant') {
      const cursor = document.createElement('span');
      cursor.className = 'streaming-cursor';
      contentElement.appendChild(cursor);
    }

    this.elements.messagesContainer.appendChild(messageElement);
    this.scrollToBottom();

    return messageElement;
  }

  private showMessages(): void {
    if (this.elements.welcomeScreen && this.elements.messagesContainer) {
      this.elements.welcomeScreen.style.display = 'none';
      this.elements.messagesContainer.style.display = 'flex';
    }
  }

  private setLoading(loading: boolean): void {
    this.client.isLoading = loading;
    
    if (this.elements.sendButton) {
      this.elements.sendButton.disabled = loading;
    }
    
    if (this.elements.loadingIndicator) {
      this.elements.loadingIndicator.classList.toggle('show', loading);
    }
  }

  private scrollToBottom(): void {
    if (this.elements.messagesContainer) {
      this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
    }
  }
}

// Initialize app when DOM is loaded
window.addEventListener('DOMContentLoaded', () => {
  new PebbleMindDesktopApp();
});
