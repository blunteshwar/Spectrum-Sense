import { LitElement, html, css } from 'lit';

class SourcesPanel extends LitElement {
    static properties = {
        sources: { type: Array }
    };

    static styles = css`
        :host {
            display: flex;
            flex-direction: column;
            height: 100%;
        }

        .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
        }

        .panel-title {
            font-size: 16px;
            font-weight: 600;
            color: #333;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .panel-title svg {
            width: 20px;
            height: 20px;
            color: #0d66d0;
        }

        .close-button {
            background: none;
            border: none;
            padding: 8px;
            cursor: pointer;
            border-radius: 8px;
            color: #666;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .close-button:hover {
            background: #f0f0f0;
            color: #333;
        }

        .close-button svg {
            width: 20px;
            height: 20px;
        }

        .sources-list {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }

        .source-card {
            background: #f8f9fb;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            border: 1px solid #e8e8e8;
            transition: all 0.2s ease;
        }

        .source-card:hover {
            border-color: #0d66d0;
            box-shadow: 0 2px 8px rgba(13, 102, 208, 0.1);
        }

        .source-title {
            font-size: 14px;
            font-weight: 600;
            color: #333;
            margin-bottom: 6px;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }

        .source-title svg {
            width: 16px;
            height: 16px;
            color: #0d66d0;
            flex-shrink: 0;
            margin-top: 2px;
        }

        .source-heading {
            font-size: 12px;
            color: #666;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .source-heading svg {
            width: 12px;
            height: 12px;
            opacity: 0.5;
        }

        .source-snippet {
            font-size: 13px;
            color: #555;
            line-height: 1.5;
            background: white;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #e8e8e8;
            margin-bottom: 12px;
        }

        .source-link {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            color: #0d66d0;
            text-decoration: none;
            padding: 8px 12px;
            background: #e8f0fe;
            border-radius: 8px;
            transition: all 0.2s ease;
        }

        .source-link:hover {
            background: #d0e0fc;
        }

        .source-link svg {
            width: 14px;
            height: 14px;
        }

        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #999;
        }

        .empty-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }

        .chunk-id {
            font-size: 11px;
            color: #999;
            font-family: monospace;
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: auto;
        }
    `;

    render() {
        return html`
            <div class="panel-header">
                <div class="panel-title">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
                    </svg>
                    Sources
                </div>
                <button class="close-button" @click=${this._close}>
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                    </svg>
                </button>
            </div>

            <div class="sources-list">
                ${this.sources?.length > 0 ? this.sources.map((source, index) => html`
                    <div class="source-card">
                        <div class="source-title">
                            <svg viewBox="0 0 24 24" fill="currentColor">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
                            </svg>
                            ${source.title || 'Untitled'}
                            <span class="chunk-id">#${index + 1}</span>
                        </div>

                        ${source.heading_path ? html`
                            <div class="source-heading">
                                <svg viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
                                </svg>
                                ${source.heading_path}
                            </div>
                        ` : ''}

                        <div class="source-snippet">
                            ${source.snippet || 'No preview available'}
                        </div>

                        ${source.url ? html`
                            <a href="${source.url}" target="_blank" class="source-link">
                                <svg viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M19 19H5V5h7V3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/>
                                </svg>
                                Open in Docs
                            </a>
                        ` : ''}
                    </div>
                `) : html`
                    <div class="empty-state">
                        <div class="empty-icon">📄</div>
                        <p>No sources available</p>
                    </div>
                `}
            </div>
        `;
    }

    _close() {
        this.dispatchEvent(new CustomEvent('close', {
            bubbles: true,
            composed: true
        }));
    }
}

customElements.define('sources-panel', SourcesPanel);

