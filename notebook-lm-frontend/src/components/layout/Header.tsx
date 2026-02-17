import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useNavigate } from 'react-router-dom';
import { LogOut, User, ChevronRight, Sun, Moon } from 'lucide-react';

interface HeaderProps {
  isCollapsed?: boolean;
  onToggleSidebar?: () => void;
}

const Header: React.FC<HeaderProps> = ({ isCollapsed = false, onToggleSidebar }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <header
      className="liquid-glass-header flex items-center justify-between px-4 sm:px-6 sticky top-0 z-20"
      style={{ minHeight: '56px', height: 'auto' }}
    >
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        {isCollapsed && onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="hidden lg:flex items-center justify-center rounded-glass-sm transition-all duration-fast touch-target"
            style={{
              width: '36px', height: '36px',
              color: 'var(--text-muted)',
              background: 'transparent',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--hover-glow)'; e.currentTarget.style.color = 'var(--accent-primary)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
            aria-label="Open navigation sidebar"
            title="Open Sidebar (Ctrl+B)"
          >
            <ChevronRight className="w-4.5 h-4.5" />
          </button>
        )}
        <h1 className="text-xs sm:text-sm font-semibold text-text_muted tracking-wide uppercase truncate">
          IntelliSense AI
        </h1>
      </div>

      <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
        {/* Liquid Glass Theme Toggle */}
        <button
          onClick={toggleTheme}
          className={`theme-toggle ${theme}`}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
        >
          <Sun
            className="absolute left-[7px] w-3.5 h-3.5 transition-all duration-normal"
            style={{
              color: theme === 'light' ? 'var(--text-inverse)' : 'var(--text-muted)',
              opacity: theme === 'light' ? 1 : 0.5,
            }}
          />
          <Moon
            className="absolute right-[7px] w-3.5 h-3.5 transition-all duration-normal"
            style={{
              color: theme === 'dark' ? 'var(--text-inverse)' : 'var(--text-muted)',
              opacity: theme === 'dark' ? 1 : 0.5,
            }}
          />
        </button>

        {user && (
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="flex items-center gap-2">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                style={{
                  background: 'var(--hover-glow)',
                  border: '1px solid var(--glass-edge)',
                }}
              >
                <User className="w-4 h-4 text-primary" />
              </div>
              <span className="text-sm text-text_secondary hidden md:inline truncate max-w-[120px]">
                {user.username}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="btn-liquid flex items-center gap-2"
              style={{ minHeight: '36px', padding: '6px 14px', fontSize: '13px' }}
              aria-label="Logout"
            >
              <LogOut className="w-4 h-4 flex-shrink-0" />
              <span className="hidden sm:inline z-content">Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
