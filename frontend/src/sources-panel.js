import { LitElement, html, css } from 'lit';

class SourcesPanel extends LitElement {
    static properties = {
        sources: { type: Array },
        themeColor: { type: String }
    };

    static styles = css`
        :host {
            display: block;
            height: 100%;
        }

        .panel-container {
            display: flex;
            flex-direction: column;
            height: 100%;
            background-color: var(--spectrum-global-color-gray-50);
            color: var(--spectrum-global-color-gray-900);
        }

        .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--spectrum-global-dimension-size-200);
            background-color: var(--spectrum-global-color-gray-50);
            border-block-end: 1px solid var(--spectrum-global-color-gray-300);
        }

        .panel-title {
            display: flex;
            align-items: center;
            gap: var(--spectrum-global-dimension-size-100);
        }

        .sources-list {
            flex: 1;
            overflow-y: auto;
            padding: var(--spectrum-global-dimension-size-200);
            background-color: var(--spectrum-global-color-gray-100);
        }

        .source-content {
            padding: var(--spectrum-global-dimension-size-200);
        }

        .source-snippet {
            background: var(--spectrum-global-color-gray-200);
            color: var(--spectrum-global-color-gray-800);
            padding: var(--spectrum-global-dimension-size-150);
            border-radius: var(--spectrum-global-dimension-size-50);
            margin-block-end: var(--spectrum-global-dimension-size-150);
            font-size: var(--spectrum-global-dimension-font-size-75);
            line-height: 1.5;
        }

        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            padding: var(--spectrum-global-dimension-size-400);
        }
    `;

    constructor() {
        super();
        this.themeColor = 'light';
    }

    render() {
        return html`
            <sp-theme theme="spectrum" color="${this.themeColor}" scale="medium" style="display: block; height: 100%;">
                <div class="panel-container">
                    <header class="panel-header">
                        <div class="panel-title">
                            <sp-icon-document></sp-icon-document>
                            <sp-help-text size="l" style="font-weight: bold;">Sources</sp-help-text>
                        </div>
                        <sp-action-button quiet size="s" @click=${this._close}>
                            <sp-icon-close slot="icon"></sp-icon-close>
                        </sp-action-button>
                    </header>

                    <div class="sources-list">
                        ${this.sources?.length > 0 
                            ? html`
                                <sp-accordion allow-multiple>
                                    ${this.sources.map((source, index) => html`
                                        <sp-accordion-item label="${source.title || 'Untitled'} #${index + 1}">
                                            <div class="source-content">
                                                ${source.heading_path ? html`
                                                    <sp-help-text size="s">
                                                        ${source.heading_path}
                                                    </sp-help-text>
                                                ` : ''}

                                                <div class="source-snippet">
                                                    ${source.snippet || 'No preview available'}
                                                </div>

                                                ${source.url ? html`
                                                    <sp-button 
                                                        variant="secondary" 
                                                        size="s"
                                                        href="${source.url}" 
                                                        target="_blank"
                                                    >
                                                        <sp-icon-link-out slot="icon"></sp-icon-link-out>
                                                        Open in Docs
                                                    </sp-button>
                                                ` : ''}
                                            </div>
                                        </sp-accordion-item>
                                    `)}
                                </sp-accordion>
                            `
                            : html`
                                <div class="empty-state">
                                    <sp-illustrated-message
                                        heading="No Sources"
                                        description="No sources are available for this response."
                                    >
                                        <sp-icon-document slot="illustration" style="width: 80px; height: 80px;"></sp-icon-document>
                                    </sp-illustrated-message>
                                </div>
                            `
                        }
                    </div>
                </div>
            </sp-theme>
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
