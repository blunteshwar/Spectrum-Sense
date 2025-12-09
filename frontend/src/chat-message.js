import { LitElement, html, css } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

class ChatMessage extends LitElement {
    static properties = {
        message: { type: Object },
        copied: { type: Boolean }
    };

    static styles = css`
        :host {
            display: block;
            margin-bottom: 20px;
            animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message-container {
            display: flex;
            gap: 12px;
            max-width: 100%;
        }

        .message-container.user {
            justify-content: flex-end;
        }

        .avatar {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            flex-shrink: 0;
        }

        .avatar.assistant {
            background: linear-gradient(135deg, #0d66d0 0%, #6e5bde 100%);
            color: white;
        }

        .avatar.user {
            background: #e0e0e0;
            color: #666;
        }

        .message-content {
            max-width: 75%;
            padding: 16px 20px;
            border-radius: 16px;
            line-height: 1.6;
            font-size: 15px;
        }

        .message-content.user {
            background: linear-gradient(135deg, #0d66d0 0%, #5a4fcf 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }

        .message-content.assistant {
            background: white;
            color: #333;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }

        .message-content.error {
            background: #fff5f5;
            border: 1px solid #ffccc7;
        }

        .message-text {
            white-space: pre-wrap;
            word-break: break-word;
        }

        .message-text p {
            margin: 0 0 12px 0;
        }

        .message-text p:last-child {
            margin-bottom: 0;
        }

        .message-text code {
            background: rgba(0, 0, 0, 0.06);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 13px;
        }

        .message-content.user .message-text code {
            background: rgba(255, 255, 255, 0.2);
        }

        .message-text pre {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 12px 0;
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
        }

        .message-text pre code {
            background: transparent;
            padding: 0;
            color: inherit;
        }

        .message-text strong {
            font-weight: 600;
        }

        .message-text ul, .message-text ol {
            margin: 8px 0;
            padding-left: 24px;
        }

        .message-text li {
            margin: 4px 0;
        }

        .message-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid rgba(0, 0, 0, 0.08);
        }

        .sources-button {
            display: flex;
            align-items: center;
            gap: 6px;
            background: #f5f5f5;
            border: none;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            color: #0d66d0;
            cursor: pointer;
            transition: all 0.2s ease;
            font-family: inherit;
        }

        .sources-button:hover {
            background: #e8f0fe;
        }

        .sources-count {
            background: #0d66d0;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        }

        .message-actions {
            display: flex;
            gap: 8px;
        }

        .action-button {
            background: transparent;
            border: none;
            padding: 6px;
            border-radius: 6px;
            cursor: pointer;
            color: #666;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .action-button:hover {
            background: #f0f0f0;
            color: #333;
        }

        .action-button svg {
            width: 16px;
            height: 16px;
        }

        .latency {
            font-size: 12px;
            color: #999;
        }

        .source-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }

        .source-chip {
            display: flex;
            align-items: center;
            gap: 6px;
            background: #f0f4f8;
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 12px;
            color: #555;
            text-decoration: none;
            transition: all 0.2s ease;
        }

        .source-chip:hover {
            background: #e0e8f0;
            color: #0d66d0;
        }

        .source-chip svg {
            width: 12px;
            height: 12px;
            opacity: 0.6;
        }
    `;

    constructor() {
        super();
        this.copied = false;
    }

    render() {
        const { role, content, sources, latency, isError } = this.message;

        return html`
            <div class="message-container ${role}">
                ${role === 'assistant' ? html`
                    <div class="avatar assistant">✨</div>
                ` : ''}

                <div class="message-content ${role} ${isError ? 'error' : ''}">
                    <div class="message-text">
                        ${unsafeHTML(this._formatContent(content))}
                    </div>

                    ${role === 'assistant' && sources?.length > 0 ? html`
                        <div class="message-footer">
                            <button class="sources-button" @click=${this._showSources}>
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
                                </svg>
                                View Sources
                                <span class="sources-count">${sources.length}</span>
                            </button>
                            <div class="message-actions">
                                ${latency ? html`
                                    <span class="latency">${latency}ms</span>
                                ` : ''}
                                <button class="action-button" @click=${this._copyContent} title="Copy">
                                    ${this.copied ? html`
                                        <svg viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                                        </svg>
                                    ` : html`
                                        <svg viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M16 1H4a2 2 0 0 0-2 2v14h2V3h12V1zm3 4H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2zm0 16H8V7h11v14z"/>
                                        </svg>
                                    `}
                                </button>
                            </div>
                        </div>

                        <div class="source-chips">
                            ${sources.slice(0, 3).map(source => html`
                                <a href="${source.url}" target="_blank" class="source-chip" title="${source.snippet}">
                                    <svg viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
                                    </svg>
                                    ${this._truncate(source.title, 30)}
                                </a>
                            `)}
                        </div>
                    ` : ''}
                </div>

                ${role === 'user' ? html`
                    <div class="avatar user">👤</div>
                ` : ''}
            </div>
        `;
    }

    _formatContent(content) {
        if (!content) return '';

        // Convert markdown-style formatting
        let formatted = content
            // Code blocks
            .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
            // Inline code
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Bold
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            // Links
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
            // Line breaks to paragraphs
            .split('\n\n')
            .filter(p => p.trim())
            .map(p => `<p>${p}</p>`)
            .join('');

        return formatted;
    }

    _truncate(text, maxLength) {
        if (!text) return '';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    _showSources() {
        this.dispatchEvent(new CustomEvent('show-sources', {
            detail: { sources: this.message.sources },
            bubbles: true,
            composed: true
        }));
    }

    async _copyContent() {
        try {
            await navigator.clipboard.writeText(this.message.content);
            this.copied = true;
            setTimeout(() => {
                this.copied = false;
            }, 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    }
}

customElements.define('chat-message', ChatMessage);

