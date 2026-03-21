import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Zap, Layers, Brain, Sliders } from 'lucide-react';
import Button from '../components/common/Button';

const LandingPage: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 sm:px-6 py-12 sm:py-16" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-3xl mx-auto text-center w-full">
        {/* Mark */}
        <div
          className="w-12 h-12 rounded-glass-sm flex items-center justify-center mx-auto mb-8"
          style={{ background: 'var(--accent-primary)' }}
        >
          <Zap className="w-5 h-5" style={{ color: 'var(--text-inverse)' }} />
        </div>

        <h1 className="heading-xl text-4xl sm:text-5xl mb-3">
          IntelliSense AI
        </h1>
        <p className="text-base text-text_secondary mb-2">
          Agentic RAG-powered intelligent notebook
        </p>
        <p className="text-sm text-text_muted mb-10 max-w-md mx-auto leading-relaxed">
          Transform your documents into an intelligent knowledge base. Ask questions,
          get answers with citations, and explore your content like never before.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-14 px-4 sm:px-0">
          {isAuthenticated ? (
            <Link to="/app/chat" className="w-full sm:w-auto">
              <Button variant="primary" size="lg" className="w-full sm:w-auto">Go to Chat</Button>
            </Link>
          ) : (
            <>
              <Link to="/login" className="w-full sm:w-auto">
                <Button variant="primary" size="lg" className="w-full sm:w-auto">Login</Button>
              </Link>
              <Link to="/signup" className="w-full sm:w-auto">
                <Button variant="secondary" size="lg" className="w-full sm:w-auto">Sign Up</Button>
              </Link>
            </>
          )}
        </div>

        {/* Features — varied weights */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            {
              icon: Layers,
              title: 'Multi-Source Retrieval',
              desc: 'Search across files, web, and YouTube simultaneously',
              prominent: true,
            },
            {
              icon: Brain,
              title: 'Intelligent Answers',
              desc: 'Accurate responses with confidence scores and citations',
              prominent: false,
            },
            {
              icon: Sliders,
              title: 'Customizable',
              desc: 'Adjust response style, length, and domain to fit your needs',
              prominent: false,
            },
          ].map(({ icon: Icon, title, desc, prominent }, i) => (
            <div
              key={title}
              className={prominent ? 'card-featured text-left' : 'card-compact text-left'}
            >
              <Icon
                className="w-4 h-4 mb-3 flex-shrink-0"
                style={{ color: prominent ? 'var(--text-primary)' : 'var(--text-muted)' }}
              />
              <h3
                className="mb-1"
                style={{
                  fontSize: prominent ? '14px' : '13px',
                  fontWeight: prominent ? 600 : 500,
                  color: 'var(--text-primary)',
                }}
              >
                {title}
              </h3>
              <p className="text-xs text-text_secondary leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
