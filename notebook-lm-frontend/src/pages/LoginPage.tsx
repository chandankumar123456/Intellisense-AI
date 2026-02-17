import React from 'react';
import { Link } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import LoginForm from '../components/auth/LoginForm';

const LoginPage: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6 py-8" style={{ background: 'var(--bg-primary)' }}>
      <div className="w-full max-w-md">
        <div className="liquid-glass-elevated rounded-glass p-5 sm:p-8">
          <div className="text-center mb-6 sm:mb-8 z-content relative">
            <Link to="/" className="inline-flex flex-col items-center gap-2.5 sm:gap-3 group">
              <div
                className="w-11 h-11 sm:w-12 sm:h-12 rounded-full flex items-center justify-center transition-transform duration-fast group-hover:scale-105"
                style={{
                  background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                  boxShadow: '0 4px 20px var(--hover-glow)',
                }}
              >
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-text_primary">IntelliSense AI</h1>
            </Link>
            <p className="text-xs sm:text-sm text-text_secondary mt-2">Sign in to your account</p>
          </div>
          <div className="z-content relative"><LoginForm /></div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
