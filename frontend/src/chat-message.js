import { LitElement, html, css } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';

class ChatMessage extends LitElement {
    static properties = {
        message: { type: Object },
        copied: { type: Boolean },
        themeColor: { type: String }
    };

    static styles = css`
        :host {
            display: block;
            margin-block-end: var(--spectrum-global-dimension-size-200);
        }

        .message-row {
            display: flex;
            gap: var(--spectrum-global-dimension-size-150);
        }

        .message-row.user {
            flex-direction: row-reverse;
        }

        .avatar-container {
            flex-shrink: 0;
        }

        .message-bubble {
            display: inline-block;
            width: auto;
            max-width: 75%;
            padding: 6px 10px;
            border-radius: 16px;
            box-shadow: var(--spectrum-alias-elevation-low);
            text-align: left;
        }

        .message-row.assistant .message-bubble {
            background: var(--spectrum-alias-background-color-secondary);
            color: var(--spectrum-alias-text-color-primary);
            border: 1px solid var(--spectrum-alias-border-color);
            border-bottom-left-radius: 4px;
        }

        .message-row.user .message-bubble {
            background: var(--spectrum-accent-color-700);
            color: #fff;
            border-bottom-right-radius: 4px;
            text-align: center;
        }

        .message-row.user .message-bubble .message-text,
        .message-row.user .message-bubble .message-text p,
        .message-row.user .message-bubble .message-text strong {
            color: inherit;
        }

        .message-text {
            white-space: pre-line;
            word-break: break-word;
            line-height: 1.2;
            color: inherit;
            margin: 0;
            padding: 0;
            display: inline-block;
            text-align: left;
        }

        .message-text p {
            margin: 0;
            padding: 0;
            display: inline;
        }

        .message-text p:last-child {
            margin: 0;
            padding: 0;
        }

        .message-text > * {
            margin: 0;
            padding: 0;
        }

        .message-text code {
            font-family: var(--spectrum-global-font-family-code);
            font-size: var(--spectrum-global-dimension-font-size-75);
            background: var(--spectrum-global-color-gray-200);
            color: var(--spectrum-global-color-gray-900);
            padding: 2px 6px;
            border-radius: var(--spectrum-global-dimension-size-50);
        }

        .message-text pre {
            background: var(--spectrum-global-color-gray-900);
            color: var(--spectrum-global-color-gray-50);
            padding: var(--spectrum-global-dimension-size-200);
            border-radius: var(--spectrum-global-dimension-size-100);
            overflow-x: auto;
            margin: var(--spectrum-global-dimension-size-150) 0;
            font-family: var(--spectrum-global-font-family-code);
            font-size: var(--spectrum-global-dimension-font-size-75);
        }

        .message-text pre code {
            background: transparent;
            padding: 0;
            color: inherit;
        }

        .message-text ul, .message-text ol {
            margin: var(--spectrum-global-dimension-size-100) 0;
            padding-inline-start: var(--spectrum-global-dimension-size-300);
            color: var(--spectrum-global-color-gray-800);
        }

        .message-text li {
            margin: var(--spectrum-global-dimension-size-50) 0;
        }

        .message-text strong {
            color: var(--spectrum-global-color-gray-900);
        }

        .message-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-block-start: var(--spectrum-global-dimension-size-150);
            margin-block-start: var(--spectrum-global-dimension-size-150);
            border-block-start: 1px solid var(--spectrum-global-color-gray-300);
        }

        .source-tags {
            margin-block-start: var(--spectrum-global-dimension-size-150);
        }

        .code-block-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--spectrum-global-color-gray-800);
            padding: var(--spectrum-global-dimension-size-75) var(--spectrum-global-dimension-size-150);
            border-radius: var(--spectrum-global-dimension-size-100) var(--spectrum-global-dimension-size-100) 0 0;
            font-size: var(--spectrum-global-dimension-font-size-50);
            color: var(--spectrum-global-color-gray-400);
            text-transform: uppercase;
            font-family: var(--spectrum-global-font-family-code);
        }

        .code-block-wrapper {
            margin: var(--spectrum-global-dimension-size-150) 0;
            border-radius: var(--spectrum-global-dimension-size-100);
            overflow: hidden;
        }

        .code-block-wrapper pre {
            margin: 0;
            border-radius: 0 0 var(--spectrum-global-dimension-size-100) var(--spectrum-global-dimension-size-100);
        }

        .actions-container {
            display: flex;
            align-items: center;
            gap: var(--spectrum-global-dimension-size-100);
        }
    `;

    constructor() {
        super();
        this.copied = false;
        this.themeColor = 'light';
    }

    render() {
        const { role, content, sources, latency, isError } = this.message;

        return html`
            <sp-theme theme="spectrum" color="${this.themeColor === 'dark' ? 'dark' : 'light'}" scale="medium" style="display: block;">
                <div class="message-row ${role}">
                    <div class="avatar-container">
                        ${role === 'assistant' 
                            ? html`<sp-avatar label="Assistant" size="500" src="https://emoji.slack-edge.com/T23RE8G4F/erc_ai_2/469a58f789f70bc8.png"></sp-avatar>`
                            : html`<sp-avatar label="You" size="500" src="https://emoji.slack-edge.com/T23RE8G4F/ruben-eyes/88e46fe99c285a6f.gif" ></sp-avatar>`
                        }
                    </div>

                    <div class="message-bubble">
                        <div class="message-text">${unsafeHTML(this._formatContent(content))}</div>${role === 'assistant' && sources?.length > 0 ? html`
                            <div class="message-footer">
                                <sp-action-button quiet size="s" @click=${this._showSources}>
                                    <sp-icon-document slot="icon"></sp-icon-document>
                                    View Sources
                                    <sp-badge size="s" variant="informative">${sources.length}</sp-badge>
                                </sp-action-button>
                                
                                <div class="actions-container">
                                    ${latency ? html`
                                        <sp-help-text size="s">${latency}ms</sp-help-text>
                                    ` : ''}
                                    <sp-action-button 
                                        quiet 
                                        size="s" 
                                        @click=${this._copyContent}
                                        title="Copy"
                                    >
                                        ${this.copied 
                                            ? html`<sp-icon-checkmark slot="icon"></sp-icon-checkmark>`
                                            : html`<sp-icon-copy slot="icon"></sp-icon-copy>`
                                        }
                                    </sp-action-button>
                                </div>
                            </div>

                            <sp-tags class="source-tags" size="s">
                                ${sources.slice(0, 3).map(source => html`
                                    <sp-tag href="${source.url}" target="_blank">
                                        ${this._truncate(source.title, 30)}
                                    </sp-tag>
                                `)}
                            </sp-tags>
                        ` : ''}
                    </div>
                </div>
            </sp-theme>
        `;
    }

    _formatContent(content) {
        if (!content) return '';

        // Extract and protect code blocks
        const codeBlocks = [];
        let processed = content.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
            const index = codeBlocks.length;
            const trimmedCode = code.trim();
            const escapedCode = this._escapeHtml(trimmedCode);
            const langLabel = this._escapeHtml(lang || 'code');
            
            const blockHtml = `
                <div class="code-block-wrapper">
                    <div class="code-block-header">
                        <span>${langLabel}</span>
                    </div>
                    <pre><code>${escapedCode}</code></pre>
                </div>
            `;
            
            codeBlocks.push(blockHtml);
            return `__CODE_BLOCK_${index}__`;
        });

        // Extract inline code
        const inlineCodes = [];
        processed = processed.replace(/`([^`]+)`/g, (match, code) => {
            const index = inlineCodes.length;
            inlineCodes.push(`<code>${this._escapeHtml(code)}</code>`);
            return `__INLINE_CODE_${index}__`;
        });

        // Escape remaining HTML
        processed = this._escapeHtml(processed);

        // Restore inline code
        inlineCodes.forEach((code, index) => {
            processed = processed.replace(`__INLINE_CODE_${index}__`, code);
        });

        // Apply markdown formatting
        processed = processed
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
                const unescapedUrl = url.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
                const sanitizedUrl = this._sanitizeUrl(unescapedUrl);
                if (!sanitizedUrl) return text;
                return `<sp-link href="${sanitizedUrl}" target="_blank">${text}</sp-link>`;
            })
            .replace(/^[\s]*[-*]\s+(.+)$/gm, '<li>$1</li>')
            .replace(/^[\s]*\d+\.\s+(.+)$/gm, '<li>$1</li>');

        // Wrap lists
        processed = processed.replace(/(<li>[\s\S]*?<\/li>)+/g, '<ul>$&</ul>');

        // Paragraphs
        const paragraphs = processed.split(/\n\n+/).filter(p => p.trim());
        processed = paragraphs.map(p => {
            p = p.trim();
            if (p.startsWith('__CODE_BLOCK_') || p.startsWith('<ul>') || p.startsWith('<div')) {
                return p;
            }
            p = p.replace(/\n/g, '<br>');
            return `<p>${p}</p>`;
        }).join('');

        // Restore code blocks
        codeBlocks.forEach((block, index) => {
            processed = processed.replace(`__CODE_BLOCK_${index}__`, block);
            processed = processed.replace(`<p>__CODE_BLOCK_${index}__</p>`, block);
        });

        return processed;
    }

    _escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    _sanitizeUrl(url) {
        if (!url) return null;
        const trimmed = url.trim().toLowerCase();
        const dangerousProtocols = ['javascript:', 'vbscript:', 'data:', 'file:'];
        for (const protocol of dangerousProtocols) {
            if (trimmed.startsWith(protocol)) return null;
        }
        const safeProtocols = ['http://', 'https://', 'mailto:', 'tel:', '#', '/'];
        const hasProtocol = /^[a-z][a-z0-9+.-]*:/i.test(url.trim());
        if (hasProtocol) {
            const isSafe = safeProtocols.some(p => trimmed.startsWith(p));
            if (!isSafe) return null;
        }
        return url.trim();
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
