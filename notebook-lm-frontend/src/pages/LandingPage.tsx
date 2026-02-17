import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Sparkles, Layers, Brain, Sliders } from 'lucide-react';
import Button from '../components/common/Button';

const LandingPage: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 sm:px-6 py-12 sm:py-16" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-4xl mx-auto text-center w-full">
        {/* Liquid glass orb */}
        <div
          className="w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center mx-auto mb-6 sm:mb-8 animate-float liquid-glass"
          style={{
            background: 'linear-gradient(135deg, var(--hover-glow), var(--active-glow))',
            boxShadow: '0 12px 48px var(--hover-glow)',
          }}
        >
          <Sparkles className="w-6 h-6 sm:w-7 sm:h-7 text-primary z-content relative" />
        </div>

        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-semibold text-text_primary mb-3 sm:mb-4 tracking-tight">
          IntelliSense AI
        </h1>
        <p className="text-base sm:text-lg lg:text-xl text-text_secondary mb-2 sm:mb-3">
          Agentic RAG-powered intelligent notebook
        </p>
        <p className="text-xs sm:text-sm text-text_muted mb-8 sm:mb-12 max-w-xl mx-auto leading-relaxed">
          Transform your documents into an intelligent knowledge base. Ask questions,
          get answers with citations, and explore your content like never before.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-10 sm:mb-16 px-4 sm:px-0">
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

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { icon: Layers, title: 'Multi-Source Retrieval', desc: 'Search across files, web, and YouTube simultaneously' },
            { icon: Brain, title: 'Intelligent Answers', desc: 'Accurate responses with confidence scores and citations' },
            { icon: Sliders, title: 'Customizable', desc: 'Adjust response style, length, and domain to fit your needs' },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="card text-left group">
              <div
                className="w-11 h-11 sm:w-12 sm:h-12 rounded-glass-sm flex items-center justify-center mb-3 sm:mb-4 z-content relative transition-all duration-fast group-hover:scale-105"
                style={{ background: 'var(--hover-glow)', border: '1px solid var(--focus-ring)' }}
              >
                <Icon className="w-5 h-5 sm:w-6 sm:h-6 text-primary" />
              </div>
              <h3 className="text-sm sm:text-base font-semibold text-text_primary mb-1.5 sm:mb-2 z-content relative">{title}</h3>
              <p className="text-xs sm:text-sm text-text_secondary leading-relaxed z-content relative">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
