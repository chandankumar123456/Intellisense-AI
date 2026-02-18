import React from 'react';
import { Link } from 'react-router-dom';
import { MessageSquare, FileText, Globe, Youtube, ArrowRight } from 'lucide-react';

const HomePage: React.FC = () => {
  const quickActions = [
    { icon: MessageSquare, title: 'Start Chatting', desc: 'Ask questions from your knowledge base', path: '/app/chat', color: 'var(--accent-primary)' },
    { icon: Globe, title: 'Web Sources', desc: 'Manage and search web sources', path: '/app/web', color: 'var(--accent-secondary)' },
    { icon: Youtube, title: 'YouTube Videos', desc: 'Index and search video content', path: '/app/youtube', color: 'var(--soft-highlight)' },
    { icon: FileText, title: 'Chat History', desc: 'View previous conversations', path: '/app/history', color: 'var(--accent-primary-light)' },
  ];

  return (
    <div className="p-4 sm:p-6 lg:p-8 overflow-y-auto h-full" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8 sm:mb-10 animate-fade-in-up">
          <h1 className="text-2xl sm:text-3xl font-semibold text-text_primary mb-2 tracking-tight">
            Welcome to IntelliSense AI
          </h1>
          <p className="text-xs sm:text-sm text-text_secondary">Your intelligent notebook powered by Agentic RAG</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 mb-8">
          {quickActions.map(({ icon: Icon, title, desc, path, color }, index) => (
            <Link
              key={path}
              to={path}
              className="group card transition-all duration-normal animate-scale-in"
              style={{
                '--card-accent': color,
                animationDelay: `${index * 100}ms`
              } as React.CSSProperties}
            >
              <div className="flex items-start justify-between z-content relative">
                <div className="flex-1 min-w-0">
                  <div
                    className="w-10 h-10 sm:w-11 sm:h-11 rounded-glass-sm flex items-center justify-center mb-3 transition-all duration-fast group-hover:scale-105 flex-shrink-0"
                    style={{ background: 'var(--hover-glow)', border: '1px solid var(--focus-ring)' }}
                  >
                    <Icon className="w-5 h-5" style={{ color }} />
                  </div>
                  <h3 className="text-sm sm:text-base font-semibold text-text_primary mb-1">{title}</h3>
                  <p className="text-xs sm:text-sm text-text_secondary leading-relaxed">{desc}</p>
                </div>
                <ArrowRight className="w-4 h-4 text-text_muted opacity-0 group-hover:opacity-100 transition-all duration-fast mt-1 group-hover:translate-x-1 flex-shrink-0 ml-2" />
              </div>
            </Link>
          ))}
        </div>

        <div className="text-center">
          <Link to="/app/chat">
            <button className="btn-primary-liquid w-full sm:w-auto" style={{ minHeight: '48px', padding: '12px 32px' }}>
              <span className="z-content relative text-base font-semibold">Get Started</span>
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
