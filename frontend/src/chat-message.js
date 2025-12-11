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
            background: #f1f3f4;
            color: #d63384;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 13px;
            border: 1px solid #e0e0e0;
        }

        .message-content.user .message-text code {
            background: rgba(255, 255, 255, 0.2);
            color: #fff;
            border-color: rgba(255, 255, 255, 0.3);
        }

        .message-text pre {
            background: #1e1e2e;
            color: #cdd6f4;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 12px 0;
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
            border: 1px solid #313244;
        }

        .message-text pre code {
            background: transparent;
            padding: 0;
            color: #cdd6f4;
            white-space: pre;
            display: block;
        }

        /* Syntax highlighting colors */
        .message-text pre .keyword { color: #cba6f7; }
        .message-text pre .string { color: #a6e3a1; }
        .message-text pre .comment { color: #6c7086; font-style: italic; }
        .message-text pre .tag { color: #89b4fa; }
        .message-text pre .attr { color: #f9e2af; }

        .code-block-wrapper {
            position: relative;
            margin: 12px 0;
        }

        .code-lang-label {
            position: absolute;
            top: 0;
            right: 0;
            background: #45475a;
            color: #bac2de;
            padding: 4px 10px;
            font-size: 11px;
            border-radius: 0 8px 0 6px;
            font-family: 'SF Mono', Monaco, monospace;
            text-transform: uppercase;
        }

        .copy-code-button {
            position: absolute;
            top: 8px;
            right: 70px;
            background: #45475a;
            border: none;
            color: #bac2de;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
            opacity: 0;
            transition: opacity 0.2s ease;
        }

        .code-block-wrapper:hover .copy-code-button {
            opacity: 1;
        }

        .copy-code-button:hover {
            background: #585b70;
            color: #cdd6f4;
        }

        .message-text strong {
            font-weight: 600;
        }

        .message-text em {
            font-style: italic;
        }

        .message-text a {
            color: #0d66d0;
            text-decoration: none;
            border-bottom: 1px solid rgba(13, 102, 208, 0.3);
            transition: all 0.2s ease;
        }

        .message-text a:hover {
            color: #0a4f9e;
            border-bottom-color: #0a4f9e;
        }

        .message-content.user .message-text a {
            color: #b3d4fc;
            border-bottom-color: rgba(179, 212, 252, 0.4);
        }

        .message-content.user .message-text a:hover {
            color: white;
            border-bottom-color: white;
        }

        .message-text ul, .message-text ol {
            margin: 8px 0;
            padding-left: 24px;
        }

        .message-text li {
            margin: 4px 0;
        }

        .message-text br + br {
            display: none;
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

        // First, extract and protect code blocks
        const codeBlocks = [];
        let processed = content.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
            const index = codeBlocks.length;
            const escapedCode = this._escapeHtml(code.trim());
            const langLabel = lang ? `<span class="code-lang-label">${lang}</span>` : '';
            codeBlocks.push(`<div class="code-block-wrapper">${langLabel}<pre><code>${escapedCode}</code></pre></div>`);
            return `__CODE_BLOCK_${index}__`;
        });

        // Apply other formatting
        processed = processed
            // Inline code (escape HTML inside)
            .replace(/`([^`]+)`/g, (match, code) => `<code>${this._escapeHtml(code)}</code>`)
            // Bold
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            // Links
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
            // Bullet lists
            .replace(/^[\s]*[-*]\s+(.+)$/gm, '<li>$1</li>')
            // Numbered lists
            .replace(/^[\s]*\d+\.\s+(.+)$/gm, '<li>$1</li>');

        // Wrap consecutive <li> tags in <ul>
        processed = processed.replace(/(<li>[\s\S]*?<\/li>)+/g, '<ul>$&</ul>');

        // Split into paragraphs (but not code block placeholders)
        const paragraphs = processed.split(/\n\n+/).filter(p => p.trim());
        processed = paragraphs.map(p => {
            p = p.trim();
            // Don't wrap code block placeholders, lists, or already-wrapped elements
            if (p.startsWith('__CODE_BLOCK_') || p.startsWith('<ul>') || p.startsWith('<div')) {
                return p;
            }
            // Replace single newlines with <br>
            p = p.replace(/\n/g, '<br>');
            return `<p>${p}</p>`;
        }).join('');

        // Restore code blocks
        codeBlocks.forEach((block, index) => {
            processed = processed.replace(`__CODE_BLOCK_${index}__`, block);
            // Also handle case where it got wrapped in <p>
            processed = processed.replace(`<p>__CODE_BLOCK_${index}__</p>`, block);
        });

        return processed;
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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

