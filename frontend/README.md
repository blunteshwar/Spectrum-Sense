# Spectrum Sense Frontend

A modern chat interface for the Spectrum RAG chatbot built with [Spectrum Web Components](https://opensource.adobe.com/spectrum-web-components/).

## Features

- 💬 Clean, responsive chat interface
- 🎨 Built with Adobe Spectrum Web Components
- 📚 Source citations with expandable panel
- ⚡ Real-time message streaming support
- 🌙 Beautiful gradient design
- 📱 Mobile-friendly responsive layout

## Quick Start

### With Docker (Recommended)

The frontend is included in the main Docker Compose setup:

```bash
cd deploy
docker compose up -d
```

Access the frontend at: http://localhost:3000

### Local Development

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```

   The dev server starts at http://localhost:3000 with hot reload.

3. **Make sure the backend API is running** on port 8000.

## Project Structure

```
frontend/
├── src/
│   ├── main.js              # Entry point, imports SWC components
│   ├── spectrum-chat-app.js # Main app component
│   ├── chat-message.js      # Message component with formatting
│   └── sources-panel.js     # Sources sidebar component
├── public/
│   └── spectrum-icon.svg    # App icon
├── index.html               # HTML entry point
├── vite.config.js           # Vite configuration
├── nginx.conf               # Production nginx config
├── Dockerfile               # Production Docker build
└── package.json
```

## Components

### `<spectrum-chat-app>`
Main application shell with header, message list, and input area.

### `<chat-message>`
Renders individual messages with:
- Markdown formatting (code blocks, bold, links)
- Copy to clipboard
- Source chip links
- Latency display

### `<sources-panel>`
Expandable panel showing detailed source information:
- Title and heading path
- Snippet preview
- Link to original documentation

## API Integration

The frontend communicates with the backend via `/api` proxy:

- `POST /api/answer` - Send query, receive answer with sources
- `GET /api/health` - Health check

In development, Vite proxies `/api` to `http://localhost:8000`.
In production, nginx handles the proxy.

## Building for Production

```bash
npm run build
```

Output is in the `dist/` directory.

## Customization

### Changing Colors

Edit the CSS custom properties in `index.html`:

```css
:root {
    --message-user-bg: #0d66d0;
    --message-assistant-bg: #ffffff;
    --accent-gradient: linear-gradient(135deg, #0d66d0 0%, #6e5bde 100%);
}
```

### Adding Suggestions

Edit the `_getSuggestions()` method in `spectrum-chat-app.js`:

```javascript
_getSuggestions() {
    return [
        'Your suggestion here',
        // ...
    ];
}
```

## Spectrum Web Components Used

- `sp-theme` - Theming
- `sp-button` - Buttons
- `sp-action-button` - Action buttons
- `sp-textfield` - Text input
- `sp-progress-circle` - Loading indicator
- `sp-link` - Links
- `sp-card` - Cards
- `sp-divider` - Dividers
- `sp-toast` - Notifications
- Various workflow icons

## Browser Support

Modern browsers with ES modules support:
- Chrome 80+
- Firefox 75+
- Safari 13.1+
- Edge 80+

