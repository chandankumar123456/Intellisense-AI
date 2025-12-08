import React from 'react';
import { Link } from 'react-router-dom';
import { MessageSquare, FileText, Globe, Youtube } from 'lucide-react';
import Button from '../components/common/Button';

const HomePage: React.FC = () => {
  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-text_primary mb-4">
            Welcome to Notebook LM
          </h1>
          <p className="text-lg text-text_secondary">
            Your intelligent notebook interface powered by Agentic RAG
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Link to="/app/chat" className="card hover:shadow-lg transition-shadow">
            <MessageSquare className="w-8 h-8 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Start Chatting</h3>
            <p className="text-text_secondary">
              Ask questions and get intelligent answers from your knowledge base
            </p>
          </Link>

          <Link to="/app/web" className="card hover:shadow-lg transition-shadow">
            <Globe className="w-8 h-8 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Web Sources</h3>
            <p className="text-text_secondary">
              Manage and search web sources for your queries
            </p>
          </Link>

          <Link to="/app/youtube" className="card hover:shadow-lg transition-shadow">
            <Youtube className="w-8 h-8 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">YouTube Videos</h3>
            <p className="text-text_secondary">
              Index and search through YouTube video content
            </p>
          </Link>

          <Link to="/app/history" className="card hover:shadow-lg transition-shadow">
            <FileText className="w-8 h-8 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Chat History</h3>
            <p className="text-text_secondary">
              View and manage your previous conversations
            </p>
          </Link>
        </div>

        <div className="text-center">
          <Link to="/app/chat">
            <Button variant="primary" size="lg">
              Get Started
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
