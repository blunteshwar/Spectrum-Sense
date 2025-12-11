import { LitElement, html, css } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import './chat-message.js';
import './sources-panel.js';

class SpectrumChatApp extends LitElement {
    static properties = {
        messages: { type: Array },
        inputValue: { type: String },
        isLoading: { type: Boolean },
        error: { type: String },
        selectedSources: { type: Array },
        showSources: { type: Boolean },
        apiBaseUrl: { type: String }
    };

    static styles = css`
        :host {
            display: flex;
            flex-direction: column;
            height: 100vh;
            background: linear-gradient(180deg, #f0f4f8 0%, #e8ecf1 100%);
        }

        .app-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 24px;
            background: linear-gradient(135deg, #0d66d0 0%, #6e5bde 100%);
            color: white;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo {
            width: 40px;
            height: 40px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }

        .app-title {
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .app-subtitle {
            font-size: 13px;
            opacity: 0.85;
            font-weight: 400;
        }

        .header-actions {
            display: flex;
            gap: 8px;
        }

        .main-content {
            display: flex;
            flex: 1;
            overflow: hidden;
        }

        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            max-width: 900px;
            margin: 0 auto;
            width: 100%;
            padding: 0 24px;
        }

        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 24px 0;
            scroll-behavior: smooth;
        }

        .messages-container::-webkit-scrollbar {
            width: 6px;
        }

        .messages-container::-webkit-scrollbar-track {
            background: transparent;
        }

        .messages-container::-webkit-scrollbar-thumb {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 3px;
        }

        .welcome-message {
            text-align: center;
            padding: 60px 24px;
            animation: fadeIn 0.5s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .welcome-icon {
            width: 80px;
            height: 80px;
            margin: 0 auto 24px;
            background: linear-gradient(135deg, #0d66d0 0%, #6e5bde 100%);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            box-shadow: 0 8px 24px rgba(13, 102, 208, 0.3);
        }

        .welcome-title {
            font-size: 28px;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 12px;
        }

        .welcome-text {
            font-size: 16px;
            color: #666;
            max-width: 500px;
            margin: 0 auto 32px;
            line-height: 1.6;
        }

        .suggestions {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            justify-content: center;
            max-width: 600px;
            margin: 0 auto;
        }

        .suggestion-chip {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 20px;
            padding: 10px 18px;
            font-size: 14px;
            color: #444;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        .suggestion-chip:hover {
            background: #0d66d0;
            color: white;
            border-color: #0d66d0;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(13, 102, 208, 0.3);
        }

        .input-container {
            padding: 20px 0 24px;
            background: transparent;
        }

        .input-wrapper {
            display: flex;
            gap: 12px;
            background: white;
            border-radius: 16px;
            padding: 8px 8px 8px 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            border: 1px solid #e0e0e0;
            transition: all 0.2s ease;
        }

        .input-wrapper:focus-within {
            border-color: #0d66d0;
            box-shadow: 0 4px 24px rgba(13, 102, 208, 0.2);
        }

        .input-field {
            flex: 1;
            border: none;
            outline: none;
            font-size: 16px;
            font-family: inherit;
            background: transparent;
            padding: 8px 0;
        }

        .input-field::placeholder {
            color: #999;
        }

        .send-button {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: linear-gradient(135deg, #0d66d0 0%, #6e5bde 100%);
            border: none;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }

        .send-button:hover:not(:disabled) {
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(13, 102, 208, 0.4);
        }

        .send-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .send-button svg {
            width: 20px;
            height: 20px;
        }

        .error-toast {
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: #d32f2f;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            animation: slideUp 0.3s ease-out;
            z-index: 1000;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translate(-50%, 20px); }
            to { opacity: 1; transform: translate(-50%, 0); }
        }

        .loading-indicator {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px 20px;
            background: white;
            border-radius: 16px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }

        .loading-dots {
            display: flex;
            gap: 4px;
        }

        .loading-dot {
            width: 8px;
            height: 8px;
            background: #0d66d0;
            border-radius: 50%;
            animation: bounce 1.4s ease-in-out infinite both;
        }

        .loading-dot:nth-child(1) { animation-delay: -0.32s; }
        .loading-dot:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }

        .loading-text {
            color: #666;
            font-size: 14px;
        }

        sources-panel {
            width: 380px;
            border-left: 1px solid #e0e0e0;
            background: white;
        }

        @media (max-width: 768px) {
            .chat-container {
                padding: 0 16px;
            }

            .app-header {
                padding: 12px 16px;
            }

            .app-title {
                font-size: 18px;
            }

            .welcome-message {
                padding: 40px 16px;
            }

            .suggestions {
                flex-direction: column;
            }

            sources-panel {
                display: none;
            }
        }
    `;

    constructor() {
        super();
        this.messages = [];
        this.inputValue = '';
        this.isLoading = false;
        this.error = null;
        this.selectedSources = [];
        this.showSources = false;
        // Use relative URL in production (proxied by nginx), direct URL in dev
        this.apiBaseUrl = window.location.hostname === 'localhost' ? '/api' : '/api';
    }

    render() {
        return html`
            <div class="app-header">
                <div class="header-left">
                    <div class="logo">✨</div>
                    <div>
                        <div class="app-title">SpectrumGPT</div>
                        <div class="app-subtitle">Adobe Spectrum Documentation Assistant</div>
                    </div>
                </div>
                <div class="header-actions">
                    <sp-action-button quiet @click=${this._clearChat}>
                        Clear Chat
                    </sp-action-button>
                </div>
            </div>

            <div class="main-content">
                <div class="chat-container">
                    <div class="messages-container" id="messages">
                        ${this.messages.length === 0 ? this._renderWelcome() : this._renderMessages()}
                        ${this.isLoading ? this._renderLoading() : ''}
                    </div>

                    <div class="input-container">
                        <div class="input-wrapper">
                            <input
                                type="text"
                                class="input-field"
                                placeholder="Ask about Spectrum components, usage, or best practices..."
                                .value=${this.inputValue}
                                @input=${this._handleInput}
                                @keydown=${this._handleKeydown}
                                ?disabled=${this.isLoading}
                            />
                            <button
                                class="send-button"
                                @click=${this._sendMessage}
                                ?disabled=${!this.inputValue.trim() || this.isLoading}
                            >
                                <svg viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>

                ${this.showSources ? html`
                    <sources-panel
                        .sources=${this.selectedSources}
                        @close=${() => this.showSources = false}
                    ></sources-panel>
                ` : ''}
            </div>

            ${this.error ? html`
                <div class="error-toast">${this.error}</div>
            ` : ''}
        `;
    }

    _renderWelcome() {
        return html`
            <div class="welcome-message">
                <div class="welcome-icon">🎨</div>
                <h1 class="welcome-title">Welcome to SpectrumGPT</h1>
                <p class="welcome-text">
                    I'm here to help you with Adobe Spectrum Design System and Spectrum Web Components.
                    Ask me about components, usage patterns, accessibility, or best practices.
                </p>
                <div class="suggestions">
                    ${this._getSuggestions().map(suggestion => html`
                        <button
                            class="suggestion-chip"
                            @click=${() => this._useSuggestion(suggestion)}
                        >
                            ${suggestion}
                        </button>
                    `)}
                </div>
            </div>
        `;
    }

    _renderMessages() {
        return this.messages.map(msg => html`
            <chat-message
                .message=${msg}
                @show-sources=${(e) => this._showSources(e.detail.sources)}
            ></chat-message>
        `);
    }

    _renderLoading() {
        return html`
            <div class="loading-indicator">
                <div class="loading-dots">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
                <span class="loading-text">Searching documentation...</span>
            </div>
        `;
    }

    _getSuggestions() {
        return [
            'How do I use sp-popover with pointerdown?',
            'What button variants are available?',
            'How do I create an accessible dialog?',
            'Explain sp-theme usage',
            'How to handle form validation?'
        ];
    }

    _handleInput(e) {
        this.inputValue = e.target.value;
    }

    _handleKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey && this.inputValue.trim()) {
            e.preventDefault();
            this._sendMessage();
        }
    }

    _useSuggestion(suggestion) {
        this.inputValue = suggestion;
        this._sendMessage();
    }

    async _sendMessage() {
        const query = this.inputValue.trim();
        if (!query || this.isLoading) return;

        // Add user message
        this.messages = [...this.messages, {
            role: 'user',
            content: query,
            timestamp: new Date()
        }];

        this.inputValue = '';
        this.isLoading = true;
        this.error = null;

        // Scroll to bottom
        await this.updateComplete;
        this._scrollToBottom();

        try {
            const response = await fetch(`${this.apiBaseUrl}/answer`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    top_k: 5
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Add assistant message
            this.messages = [...this.messages, {
                role: 'assistant',
                content: data.answer,
                sources: data.sources,
                latency: data.meta?.latency_ms,
                timestamp: new Date()
            }];

        } catch (err) {
            console.error('Error:', err);
            this.error = 'Failed to get response. Please check if the API is running.';
            setTimeout(() => this.error = null, 5000);

            // Add error message
            this.messages = [...this.messages, {
                role: 'assistant',
                content: 'Sorry, I encountered an error while processing your request. Please make sure the backend API is running and try again.',
                isError: true,
                timestamp: new Date()
            }];
        } finally {
            this.isLoading = false;
            await this.updateComplete;
            this._scrollToBottom();
        }
    }

    _scrollToBottom() {
        const container = this.shadowRoot.querySelector('#messages');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    _showSources(sources) {
        this.selectedSources = sources;
        this.showSources = true;
    }

    _clearChat() {
        this.messages = [];
        this.selectedSources = [];
        this.showSources = false;
    }
}

customElements.define('spectrum-chat-app', SpectrumChatApp);

