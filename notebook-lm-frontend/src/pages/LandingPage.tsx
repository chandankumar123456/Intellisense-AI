import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Button from '../components/common/Button';

const LandingPage: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/10 via-background to-primary/5">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-bold text-text_primary mb-6">
            Notebook LM
          </h1>
          <p className="text-xl text-text_secondary mb-8">
            Agentic RAG-powered intelligent notebook interface
          </p>
          <p className="text-lg text-text_secondary mb-12 max-w-2xl mx-auto">
            Transform your documents into an intelligent knowledge base. Ask questions,
            get answers with citations, and explore your content like never before.
          </p>

          <div className="flex gap-4 justify-center">
            {isAuthenticated ? (
              <Link to="/app/chat">
                <Button variant="primary" size="lg">
                  Go to Chat
                </Button>
              </Link>
            ) : (
              <>
                <Link to="/login">
                  <Button variant="primary" size="lg">
                    Login
                  </Button>
                </Link>
                <Link to="/signup">
                  <Button variant="secondary" size="lg">
                    Sign Up
                  </Button>
                </Link>
              </>
            )}
          </div>

          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="card">
              <h3 className="text-xl font-semibold mb-2">Multi-Source Retrieval</h3>
              <p className="text-text_secondary">
                Search across your files, web sources, and YouTube videos simultaneously
              </p>
            </div>
            <div className="card">
              <h3 className="text-xl font-semibold mb-2">Intelligent Answers</h3>
              <p className="text-text_secondary">
                Get accurate responses with confidence scores and source citations
              </p>
            </div>
            <div className="card">
              <h3 className="text-xl font-semibold mb-2">Customizable</h3>
              <p className="text-text_secondary">
                Adjust response style, length, and domain to match your needs
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
