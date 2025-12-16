import { LitElement, html, css } from 'lit';
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
        apiBaseUrl: { type: String },
        themeColor: { type: String }
    };

    static styles = css`
        :host {
            display: block;
            height: 100%;
        }

        .app-container {
            display: flex;
            flex-direction: column;
            height: 100%;
            background-color: var(--spectrum-global-color-gray-100);
            color: var(--spectrum-global-color-gray-900);
        }

        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--spectrum-global-dimension-size-200);
            background-color: var(--spectrum-global-color-gray-50);
            border-block-end: 1px solid var(--spectrum-global-color-gray-300);
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: var(--spectrum-global-dimension-size-150);
        }

        .header-logo {
            width: 40px;
            height: 40px;
            border-radius: var(--spectrum-global-dimension-size-50);
            object-fit: contain;
        }

        .header-text {
            display: flex;
            flex-direction: column;
            gap: 0;
            margin-top: 5px;
        }

        .header-text sp-help-text:first-child {
            margin-bottom: -15px;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: var(--spectrum-global-dimension-size-150);
        }

        .theme-switch-wrapper {
            display: flex;
            align-items: center;
            position: relative;
            padding-right: 35px;
           
        }

        .theme-label {
            font-size: var(--spectrum-global-dimension-font-size-75);
            color: var(--spectrum-global-color-gray-700);
            margin-right: var(--spectrum-global-dimension-size-100);
        }

        .theme-label-dark {
            font-size: var(--spectrum-global-dimension-font-size-75);
            color: var(--spectrum-global-color-gray-700);
            position: relative;
            left: -10%;
            
        }

        .main-content {
            display: flex;
            flex: 1;
            overflow: hidden;
            background-color: var(--spectrum-global-color-gray-100);
        }

        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            max-width: 900px;
            margin: 0 auto;
            width: 100%;
            padding: var(--spectrum-global-dimension-size-200);
        }

        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: var(--spectrum-global-dimension-size-200) 0;
        }

        .input-area {
            display: flex;
            gap: var(--spectrum-global-dimension-size-100);
            padding: var(--spectrum-global-dimension-size-200) 0;
        }

        .input-area sp-textfield {
            flex: 1;
        }

        .welcome-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: var(--spectrum-global-dimension-size-600);
            text-align: center;
        }

        .suggestions {
            display: flex;
            flex-wrap: wrap;
            gap: var(--spectrum-global-dimension-size-100);
            justify-content: center;
            margin-top: var(--spectrum-global-dimension-size-300);
        }

        .loading-container {
            display: flex;
            align-items: center;
            gap: var(--spectrum-global-dimension-size-150);
            padding: var(--spectrum-global-dimension-size-200);
            background-color: var(--spectrum-global-color-gray-50);
            border-radius: var(--spectrum-global-dimension-size-100);
        }

        .loading-container sp-progress-circle {
            display: block;
        }

        .loading-container sp-help-text {
            display: flex;
            align-items: center;
            line-height: 1;
            position: relative;
            top: -1px;
        }

        sources-panel {
            width: 380px;
            border-inline-start: 1px solid var(--spectrum-global-color-gray-300);
        }

        .toast-container {
            position: fixed;
            bottom: var(--spectrum-global-dimension-size-300);
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
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
        this.apiBaseUrl = window.location.hostname === 'localhost' ? '/api' : '/api';
        this.themeColor = 'light';
    }

    render() {
        return html`
            <sp-theme theme="spectrum" color="${this.themeColor === 'dark' ? 'dark' : 'light'}" scale="medium" style="display: block; height: 100%;">
                <div class="app-container">
                    <!-- Header -->
                    <header class="header">
                        <div class="header-left">
                            <img 
                                src="https://emoji.slack-edge.com/T23RE8G4F/adobe-icon2/ddd8d70e107af733.png" 
                                alt="Adobe Logo" 
                                class="header-logo"
                            />
                            <div class="header-text">
                                <sp-help-text size="l" style="font-weight: bold;">Spectrum Sense</sp-help-text>
                                <sp-help-text size="s">Adobe Spectrum Documentation Assistant</sp-help-text>
                            </div>
                        </div>
                        <div class="header-actions">
                            <div class="theme-switch-wrapper">
                                <span class="theme-label">Light</span>
                                <sp-switch 
                                    .checked=${this.themeColor === 'dark'}
                                    @change=${this._handleThemeChange}
                                ></sp-switch>
                                <span class="theme-label-dark">Dark</span>
                            </div>
                            <sp-action-button quiet @click=${this._clearChat}>
                                <sp-icon-delete slot="icon"></sp-icon-delete>
                                Clear Chat
                            </sp-action-button>
                        </div>
                    </header>

                    <!-- Main Content -->
                    <div class="main-content">
                        <div class="chat-area">
                            <!-- Messages -->
                            <div class="messages-container" id="messages">
                                ${this.messages.length === 0 ? this._renderWelcome() : this._renderMessages()}
                                ${this.isLoading ? this._renderLoading() : ''}
                            </div>

                            <!-- Input Area -->
                            <div class="input-area">
                                <sp-textfield
                                    placeholder="Ask about Spectrum components, usage, or best practices..."
                                    .value=${this.inputValue}
                                    @input=${this._handleInput}
                                    @keydown=${this._handleKeydown}
                                    ?disabled=${this.isLoading}
                                    size="l"
                                ></sp-textfield>
                                <sp-button
                                    variant="accent"
                                    @click=${this._sendMessage}
                                    ?disabled=${!this.inputValue.trim() || this.isLoading}
                                    size="l"
                                >
                                    <sp-icon-send slot="icon"></sp-icon-send>
                                    Send
                                </sp-button>
                            </div>
                        </div>

                        <!-- Sources Panel -->
                        ${this.showSources ? html`
                            <sources-panel
                                .sources=${this.selectedSources}
                                .themeColor=${this.themeColor}
                                @close=${() => this.showSources = false}
                            ></sources-panel>
                        ` : ''}
                    </div>

                    <!-- Error Toast -->
                    ${this.error ? html`
                        <div class="toast-container">
                            <sp-toast variant="negative" open @close=${() => this.error = null}>
                                ${this.error}
                            </sp-toast>
                        </div>
                    ` : ''}
                </div>
            </sp-theme>
        `;
    }

    _renderWelcome() {
        return html`
            <div class="welcome-container">
                <sp-illustrated-message heading="Welcome to Spectrum Sense">
                    <sp-icon-chat slot="illustration" style="width: 100px; height: 100px;"></sp-icon-chat>
                    <sp-help-text size="m" slot="description">
                        I'm here to help you with Adobe Spectrum Design System and Spectrum Web Components. 
                        Ask me about components, usage patterns, accessibility, or best practices.
                    </sp-help-text>
                </sp-illustrated-message>

                <div class="suggestions">
                    ${this._getSuggestions().map(suggestion => html`
                        <sp-action-button
                            @click=${() => this._useSuggestion(suggestion)}
                        >
                            ${suggestion}
                        </sp-action-button>
                    `)}
                </div>
            </div>
        `;
    }

    _renderMessages() {
        return this.messages.map(msg => html`
            <chat-message
                .message=${msg}
                .themeColor=${this.themeColor}
                @show-sources=${(e) => this._showSources(e.detail.sources)}
            ></chat-message>
        `);
    }

    _renderLoading() {
        return html`
            <div class="loading-container">
                <sp-progress-circle size="s" indeterminate></sp-progress-circle>
                <sp-help-text>Searching documentation...</sp-help-text>
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

        this.messages = [...this.messages, {
            role: 'user',
            content: query,
            timestamp: new Date()
        }];

        this.inputValue = '';
        this.isLoading = true;
        this.error = null;

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

    _handleThemeChange(e) {
        this.themeColor = e.target.checked ? 'dark' : 'light';
        this.requestUpdate();
        // Also update the root theme in index.html
        const rootTheme = document.querySelector('sp-theme');
        if (rootTheme) {
            rootTheme.color = this.themeColor;
        }
    }
}

customElements.define('spectrum-chat-app', SpectrumChatApp);
