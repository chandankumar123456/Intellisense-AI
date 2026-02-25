import React from 'react';
import { Link } from 'react-router-dom';
import { Home, ArrowLeft, Sparkles } from 'lucide-react';

const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-md w-full text-center">
        {/* Liquid glass orb */}
        <div
          className="w-16 h-16 sm:w-20 sm:h-20 rounded-full flex items-center justify-center mx-auto mb-5 sm:mb-6 liquid-glass"
          style={{
            background: 'linear-gradient(135deg, var(--hover-glow), var(--active-glow))',
            boxShadow: '0 12px 48px var(--hover-glow)',
          }}
        >
          <Sparkles className="w-6 h-6 sm:w-8 sm:h-8 z-content relative" style={{ color: 'var(--accent-primary)' }} />
        </div>

        <h1
          className="text-7xl sm:text-8xl font-bold mb-3 sm:mb-4"
          style={{
            background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          404
        </h1>
        <h2 className="text-xl sm:text-2xl font-semibold text-text_primary mb-2 sm:mb-3">Page Not Found</h2>
        <p className="text-sm text-text_muted mb-6 sm:mb-8 max-w-xs mx-auto leading-relaxed">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center px-4 sm:px-0">
          <Link to="/" className="w-full sm:w-auto">
            <button className="btn-primary-liquid w-full sm:w-auto" style={{ minHeight: '42px', padding: '0 24px' }}>
              <Home className="w-4 h-4 z-content relative" />
              <span className="z-content relative">Go Home</span>
            </button>
          </Link>
          <button
            onClick={() => window.history.back()}
            className="btn-liquid w-full sm:w-auto"
            style={{ minHeight: '42px', padding: '0 24px' }}
          >
            <ArrowLeft className="w-4 h-4 z-content relative" />
            <span className="z-content relative">Go Back</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotFoundPage;
