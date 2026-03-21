import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { LogOut, User, ChevronRight, Sun, Moon } from 'lucide-react';

interface HeaderProps {
  isCollapsed?: boolean;
  onToggleSidebar?: () => void;
}

const pageLabels: Record<string, string> = {
  '/app/home': 'Home',
  '/app/chat': 'Chat',
  '/app/history': 'History',
  '/app/web': 'Web Sources',
  '/app/youtube': 'YouTube',
  '/app/knowledge': 'My Knowledge',
  '/app/verification': 'Verification',
  '/app/admin': 'Admin',
  '/app/settings': 'Settings',
};

const Header: React.FC<HeaderProps> = ({ isCollapsed = false, onToggleSidebar }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => { logout(); navigate('/login'); };
  const pageLabel = pageLabels[location.pathname] ?? 'IntelliSense AI';

  return (
    <header
      className="liquid-glass-header flex items-center justify-between px-4 sm:px-5"
      style={{ height: '52px' }}
    >
      <div className="flex items-center gap-2 min-w-0">
        {isCollapsed && onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="hidden lg:flex items-center justify-center rounded-glass-sm transition-all duration-fast"
            style={{ width: '32px', height: '32px', color: 'var(--text-muted)', background: 'transparent' }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--hover-glow)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
            aria-label="Open navigation sidebar"
            title="Open Sidebar (Ctrl+B)"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
        <span className="text-sm font-semibold text-text_primary tracking-tight truncate">
          {pageLabel}
        </span>
      </div>

      <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className={`theme-toggle ${theme}`}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
        >
          <Sun
            className="absolute left-[6px] w-3 h-3 transition-all duration-normal"
            style={{ color: theme === 'light' ? 'var(--text-inverse)' : 'var(--text-muted)', opacity: theme === 'light' ? 1 : 0.4 }}
          />
          <Moon
            className="absolute right-[6px] w-3 h-3 transition-all duration-normal"
            style={{ color: theme === 'dark' ? 'var(--text-inverse)' : 'var(--text-muted)', opacity: theme === 'dark' ? 1 : 0.4 }}
          />
        </button>

        {user && (
          <div className="flex items-center gap-2 sm:gap-2.5">
            <div className="flex items-center gap-1.5">
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ background: 'var(--glass-elevated)', border: '1px solid var(--border-subtle)' }}
              >
                <User className="w-3.5 h-3.5 text-text_secondary" />
              </div>
              <span className="text-xs text-text_secondary hidden md:inline truncate max-w-[100px]">
                {user.username}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="btn-liquid flex items-center gap-1.5 text-xs"
              style={{ minHeight: '32px', padding: '4px 12px' }}
              aria-label="Logout"
            >
              <LogOut className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
