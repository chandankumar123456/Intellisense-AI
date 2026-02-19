import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useChat } from '../../contexts/ChatContext';
import { useAuth } from '../../contexts/AuthContext';
import {
  Home, MessageSquare, Clock, Globe, Youtube, Settings,
  Menu, X, ShieldCheck, Plus, PanelLeftClose, Sparkles, Shield, BookOpen,
} from 'lucide-react';

interface NavItem { icon: React.ElementType; label: string; path: string; adminOnly?: boolean; }

const navItems: NavItem[] = [
  { icon: Home, label: 'Home', path: '/app/home' },
  { icon: MessageSquare, label: 'Chat', path: '/app/chat' },
  { icon: Clock, label: 'History', path: '/app/history' },
  { icon: Globe, label: 'Web', path: '/app/web' },
  { icon: Youtube, label: 'YouTube', path: '/app/youtube' },
  { icon: BookOpen, label: 'My Knowledge', path: '/app/knowledge' },
  { icon: ShieldCheck, label: 'Verification', path: '/app/verification' },
  { icon: Shield, label: 'Admin', path: '/app/admin', adminOnly: true },
  { icon: Settings, label: 'Settings', path: '/app/settings' },
];

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isCollapsed, onToggleCollapse }) => {
  const location = useLocation();
  const { clearHistory } = useChat();
  const { user } = useAuth();
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // Filter out admin-only items for non-admin users
  const visibleNavItems = navItems.filter(
    (item) => !item.adminOnly || (user as any)?.role === 'admin'
  );

  useEffect(() => { setIsMobileOpen(false); }, [location.pathname]);
  useEffect(() => {
    const h = () => { if (window.innerWidth >= 1024) setIsMobileOpen(false); };
    window.addEventListener('resize', h);
    return () => window.removeEventListener('resize', h);
  }, []);

  // Touch gestures
  useEffect(() => {
    let sX = 0, sY = 0;
    const ts = (e: TouchEvent) => { sX = e.touches[0].clientX; sY = e.touches[0].clientY; };
    const te = (e: TouchEvent) => {
      const eX = e.changedTouches[0].clientX;
      const dX = eX - sX, aY = Math.abs(e.changedTouches[0].clientY - sY);
      if (sX < 30 && dX > 60 && aY < 40 && isCollapsed) onToggleCollapse();
      if (dX < -60 && aY < 40 && !isCollapsed && window.innerWidth < 1024) setIsMobileOpen(false);
    };
    window.addEventListener('touchstart', ts, { passive: true });
    window.addEventListener('touchend', te, { passive: true });
    return () => { window.removeEventListener('touchstart', ts); window.removeEventListener('touchend', te); };
  }, [isCollapsed, onToggleCollapse]);

  return (
    <>
      {/* Persistent restore — liquid glass pulse */}
      {isCollapsed && (
        <button
          onClick={onToggleCollapse}
          className="sidebar-restore hidden lg:flex"
          aria-label="Open navigation sidebar"
          aria-expanded="false"
          title="Open Sidebar (Ctrl+B)"
        >
          <Menu className="w-5 h-5" />
        </button>
      )}

      {/* Mobile toggle */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="lg:hidden fixed z-50 liquid-glass rounded-glass transition-all duration-fast active:scale-[0.92] flex items-center justify-center"
        style={{
          top: '10px', left: '10px',
          width: '44px', height: '44px',
        }}
        aria-label="Toggle menu"
      >
        {isMobileOpen ? <X className="w-5 h-5 text-text_secondary" /> : <Menu className="w-5 h-5 text-text_secondary" />}
      </button>

      {/* Mobile backdrop */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 animate-fade-in"
          style={{ background: 'rgba(0,0,0,0.15)', backdropFilter: 'blur(3px)' }}
          onClick={() => setIsMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar — liquid glass sheet */}
      <aside
        className={`
          ${isCollapsed ? 'w-0 lg:w-0 overflow-hidden' : 'w-sidebar'}
          ${isMobileOpen ? 'translate-x-0 w-sidebar' : '-translate-x-full lg:translate-x-0'}
          ${isCollapsed ? 'lg:-translate-x-full' : 'lg:translate-x-0'}
          fixed left-0 top-0 h-screen z-40
          flex flex-col
        `}
        style={{
          background: 'var(--glass-elevated)',
          backdropFilter: `blur(var(--glass-blur-heavy))`,
          WebkitBackdropFilter: `blur(var(--glass-blur-heavy))`,
          borderRight: '1px solid var(--glass-edge)',
          boxShadow: '10px 0 40px var(--glass-shadow-lg)',
          transition: 'transform 400ms cubic-bezier(0.2, 0.8, 0.2, 1), width 400ms cubic-bezier(0.2, 0.8, 0.2, 1)',
        }}
        aria-label="Navigation sidebar"
      >
        {/* Logo */}
        <div className="p-4 sm:p-5 z-content">
          <div className="flex items-center justify-between mb-5">
            <Link to="/app/home" className="flex items-center gap-2.5 group min-w-0">
              <div
                className="w-9 h-9 rounded-glass-sm flex items-center justify-center flex-shrink-0 transition-all duration-fast group-hover:scale-105"
                style={{
                  background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                  boxShadow: '0 4px 16px var(--hover-glow)',
                }}
              >
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <h2 className="text-lg font-bold text-text_primary whitespace-nowrap tracking-tight truncate">
                IntelliSense AI
              </h2>
            </Link>
            <button
              onClick={onToggleCollapse}
              className="hidden lg:flex items-center justify-center rounded-glass-sm transition-all duration-fast flex-shrink-0"
              style={{
                width: '36px', height: '36px',
                background: 'transparent',
                color: 'var(--text-muted)',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--hover-glow)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              aria-label="Collapse sidebar"
              aria-expanded="true"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          {/* New Chat — liquid gradient */}
          <button
            onClick={clearHistory}
            className="w-full btn-primary-liquid flex items-center justify-center gap-2"
            style={{ minHeight: '44px', marginBottom: '12px' }}
            aria-label="New chat"
          >
            <Plus className="w-5 h-5 flex-shrink-0" />
            <span className="z-content font-semibold">New Chat</span>
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 pb-4 space-y-1 z-content" role="navigation">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-item relative group
                  ${isActive ? 'text-primary font-medium' : 'text-text_secondary hover:text-text_primary'}`}
                style={isActive ? {
                  background: 'var(--hover-glow)',
                  boxShadow: 'inset 0 0 0 1px rgba(122,140,255,0.15)',
                } : undefined}
                onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
                aria-current={isActive ? 'page' : undefined}
              >
                {isActive && (
                  <div
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full"
                    style={{ background: 'linear-gradient(180deg, var(--accent-primary), var(--accent-secondary))' }}
                  />
                )}
                <Icon className={`w-[18px] h-[18px] flex-shrink-0 transition-transform duration-fast ${!isActive ? 'group-hover:scale-110' : ''}`} />
                <span className="text-sm truncate">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
};

export default Sidebar;
