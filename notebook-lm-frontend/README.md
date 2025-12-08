# Notebook LM Frontend

Agentic RAG-powered intelligent notebook interface built with React, TypeScript, and Tailwind CSS.

## Features

- ✅ JWT-based authentication
- ✅ Session management with Redis
- ✅ Real-time chat interface
- ✅ Multi-source retrieval (vector, keyword, web, youtube)
- ✅ Retrieval trace visualization
- ✅ Confidence score display
- ✅ User preference controls
- ✅ Conversation history
- ✅ Citation tracking
- ✅ Responsive design
- ✅ Error handling
- ✅ Loading states

## Tech Stack

- **Framework**: React 18+ with TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Context API + useReducer
- **HTTP Client**: Axios
- **Routing**: React Router v6
- **Icons**: Lucide React
- **Toast Notifications**: react-hot-toast
- **Markdown Rendering**: react-markdown

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Backend API running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file in the root directory:
```env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_ENV=development
REACT_APP_ENABLE_ANALYTICS=false
```

3. Start the development server:
```bash
npm start
```

The app will open at `http://localhost:3000`.

## Project Structure

```
src/
├── components/
│   ├── auth/          # Authentication components
│   ├── chat/          # Chat interface components
│   ├── common/        # Reusable UI components
│   └── layout/        # Layout components
├── contexts/          # React Context providers
├── hooks/             # Custom React hooks
├── pages/             # Page components
├── services/          # API service layer
├── types/             # TypeScript type definitions
└── utils/             # Utility functions
```

## Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm eject` - Eject from Create React App

## API Integration

The frontend communicates with the backend API at the base URL specified in `.env`. Key endpoints:

- `/auth/login` - User login
- `/auth/signup` - User registration
- `/auth/me` - Token verification
- `/session/create` - Create session
- `/v1/chat/query` - Send chat query

## Features Overview

### Authentication
- Secure JWT-based authentication
- Protected routes
- Auto token verification
- Session management

### Chat Interface
- Real-time messaging
- Markdown support
- Code syntax highlighting
- Citation links
- Confidence scores
- Retrieval trace visualization

### Source Management
- My Files tab
- Web sources management
- YouTube video indexing
- User preferences

## Development

The project uses:
- TypeScript for type safety
- Tailwind CSS for styling
- React Context for state management
- Axios for HTTP requests
- React Router for navigation

## License

MIT