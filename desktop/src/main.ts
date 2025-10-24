import { invoke } from '@tauri-apps/api/core';

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
  backendStarted: boolean;
}

interface BackendStatus {
  running: boolean;
  port: number;
  message: string;
}

interface ChatResponse {
  response: string;
  model: string;
  tokens?: number;
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
      backendStarted: false
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
    this.startBackend();
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

  private async startBackend(): Promise<void> {
    this.updateConnectionStatus('connecting', 'Starting PebbleMind backend...');

    try {
      const status = await invoke<BackendStatus>('start_backend');

      if (status.running) {
        this.client.backendStarted = true;
        this.client.isConnected = true;
        this.updateConnectionStatus('connected', 'Backend ready');

        // Check available models
        await this.checkModelStatus();
      } else {
        throw new Error(status.message || 'Failed to start backend');
      }
    } catch (error) {
      console.error('Failed to start backend:', error);
      this.updateConnectionStatus('disconnected', 'Backend failed to start - Click to retry');
      this.showConnectionError();

      // Retry after 5 seconds
      setTimeout(() => this.startBackend(), 5000);
    }
  }

  private async checkConnection(): Promise<void> {
    this.updateConnectionStatus('connecting', 'Checking backend status...');

    try {
      const status = await invoke<BackendStatus>('get_backend_status');

      if (status.running) {
        this.client.isConnected = true;
        this.updateConnectionStatus('connected', 'Connected');

        // Check model status
        await this.checkModelStatus();
      } else {
        throw new Error('Backend not running');
      }
    } catch (error) {
      this.client.isConnected = false;
      this.updateConnectionStatus('disconnected', 'Disconnected - Click to retry');
      console.error('Connection failed:', error);

      // Show connection error
      this.showConnectionError();

      // Try to restart backend
      setTimeout(() => this.startBackend(), 5000);
    }
  }

  private async checkModelStatus(): Promise<void> {
    try {
      const models = await invoke<any[]>('list_available_models');
      console.log('Available models:', models);
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
        <strong>Unable to start PebbleMind backend</strong><br>
        <small>Make sure PebbleMind is properly installed and accessible in your PATH</small>
      </div>
    `;

    this.elements.messagesContainer.appendChild(errorElement);
    this.scrollToBottom();
  }

  private async switchModel(modelSize: string): Promise<void> {
    if (!this.client.isConnected || this.client.isLoading) {
      return;
    }

    const oldModel = this.client.currentModel;
    this.client.currentModel = modelSize;
    this.updateConnectionStatus('connecting', `Switching to ${modelSize.toUpperCase()} model...`);

    try {
      await invoke('switch_model', { modelSize: modelSize });

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

      // Reset to old model
      this.client.currentModel = oldModel;
      if (this.elements.modelSelector) {
        this.elements.modelSelector.value = oldModel;
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
    // Create assistant message
    const assistantMessage: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: false
    };

    const messageElement = this.addMessage(assistantMessage);
    const contentElement = messageElement.querySelector('.message-content') as HTMLElement;

    try {
      // Use Tauri command to send chat message
      // Note: For now using non-streaming. Streaming would require WebSocket or event-based approach
      const response = await invoke<ChatResponse>('send_chat_message', {
        message: message,
        systemPrompt: null
      });

      // Simulate streaming effect for better UX
      const words = response.response.split(' ');
      for (let i = 0; i < words.length; i++) {
        assistantMessage.content += (i > 0 ? ' ' : '') + words[i];
        contentElement.textContent = assistantMessage.content;
        this.scrollToBottom();

        // Small delay between words for streaming effect
        await new Promise(resolve => setTimeout(resolve, 30));
      }

    } catch (error) {
      console.error('Chat request failed:', error);

      // Show error message
      assistantMessage.content = `Sorry, I encountered an error: ${error}. Please make sure the PebbleMind backend is running properly.`;
      contentElement.textContent = assistantMessage.content;
    }
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
