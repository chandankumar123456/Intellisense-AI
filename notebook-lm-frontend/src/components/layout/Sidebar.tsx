import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useChat } from '../../contexts/ChatContext';
import { useAuth } from '../../contexts/AuthContext';
import {
  Home, MessageSquare, Clock, Globe, Youtube, Settings,
  Menu, X, ShieldCheck, Plus, PanelLeftClose, Zap, Shield, BookOpen,
} from 'lucide-react';

interface NavItem { icon: React.ElementType; label: string; path: string; adminOnly?: boolean; }

const navGroups = [
  {
    label: 'Workspace',
    items: [
      { icon: Home, label: 'Home', path: '/app/home' },
      { icon: MessageSquare, label: 'Chat', path: '/app/chat' },
      { icon: Clock, label: 'History', path: '/app/history' },
    ] as NavItem[],
  },
  {
    label: 'Sources',
    items: [
      { icon: Globe, label: 'Web', path: '/app/web' },
      { icon: Youtube, label: 'YouTube', path: '/app/youtube' },
      { icon: BookOpen, label: 'My Knowledge', path: '/app/knowledge' },
    ] as NavItem[],
  },
  {
    label: 'Tools',
    items: [
      { icon: ShieldCheck, label: 'Verification', path: '/app/verification' },
      { icon: Shield, label: 'Admin', path: '/app/admin', adminOnly: true },
      { icon: Settings, label: 'Settings', path: '/app/settings' },
    ] as NavItem[],
  },
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

  useEffect(() => { setIsMobileOpen(false); }, [location.pathname]);
  useEffect(() => {
    const h = () => { if (window.innerWidth >= 1024) setIsMobileOpen(false); };
    window.addEventListener('resize', h);
    return () => window.removeEventListener('resize', h);
  }, []);

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
      {/* Restore button when collapsed */}
      {isCollapsed && (
        <button
          onClick={onToggleCollapse}
          className="sidebar-restore hidden lg:flex"
          aria-label="Open navigation sidebar"
          aria-expanded="false"
          title="Open Sidebar (Ctrl+B)"
        >
          <Menu className="w-4 h-4" />
        </button>
      )}

      {/* Mobile toggle */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="lg:hidden fixed z-50 liquid-glass rounded-glass transition-all duration-fast active:scale-[0.92] flex items-center justify-center"
        style={{ top: '10px', left: '10px', width: '40px', height: '40px' }}
        aria-label="Toggle menu"
      >
        {isMobileOpen
          ? <X className="w-4 h-4 text-text_secondary" />
          : <Menu className="w-4 h-4 text-text_secondary" />}
      </button>

      {/* Mobile backdrop */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 animate-fade-in"
          style={{ background: 'rgba(0,0,0,0.3)' }}
          onClick={() => setIsMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          ${isCollapsed ? 'w-0 lg:w-0 overflow-hidden' : 'w-sidebar'}
          ${isMobileOpen ? 'translate-x-0 w-sidebar' : '-translate-x-full lg:translate-x-0'}
          ${isCollapsed ? 'lg:-translate-x-full' : 'lg:translate-x-0'}
          fixed left-0 top-0 h-screen z-40
          flex flex-col
        `}
        style={{
          background: 'var(--glass-surface)',
          borderRight: '1px solid var(--border-subtle)',
          boxShadow: '1px 0 0 var(--border-subtle)',
          transition: 'transform 280ms cubic-bezier(0.22, 1, 0.36, 1), width 280ms cubic-bezier(0.22, 1, 0.36, 1)',
        }}
        aria-label="Navigation sidebar"
      >
        {/* Logo area */}
        <div className="px-4 pt-5 pb-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center justify-between mb-4">
            <Link to="/app/home" className="flex items-center gap-2.5 group min-w-0">
              <div
                className="w-7 h-7 rounded-glass-sm flex items-center justify-center flex-shrink-0"
                style={{ background: 'var(--accent-primary)' }}
              >
                <Zap className="w-3.5 h-3.5" style={{ color: 'var(--text-inverse)' }} />
              </div>
              <span className="text-sm font-bold text-text_primary tracking-tight truncate">
                IntelliSense
              </span>
            </Link>
            <button
              onClick={onToggleCollapse}
              className="hidden lg:flex items-center justify-center rounded-glass-sm transition-all duration-fast flex-shrink-0"
              style={{ width: '32px', height: '32px', color: 'var(--text-muted)', background: 'transparent' }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--hover-glow)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
              aria-label="Collapse sidebar"
              aria-expanded="true"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          {/* New Chat */}
          <button
            onClick={clearHistory}
            className="w-full btn-primary-liquid flex items-center justify-center gap-2"
            style={{ minHeight: '36px', fontSize: '13px' }}
            aria-label="New chat"
          >
            <Plus className="w-4 h-4 flex-shrink-0" />
            <span className="font-semibold">New Chat</span>
          </button>
        </div>

        {/* Navigation — grouped */}
        <nav className="flex-1 overflow-y-auto py-3 z-content" role="navigation">
          {navGroups.map((group) => {
            const visibleItems = group.items.filter(
              (item) => !item.adminOnly || (user as any)?.role === 'admin'
            );
            if (visibleItems.length === 0) return null;
            return (
              <div key={group.label} className="mb-4">
                <div className="px-4 mb-1">
                  <span className="label-sm">{group.label}</span>
                </div>
                <div className="px-2 space-y-0.5">
                  {visibleItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = location.pathname === item.path;
                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        className={`nav-item relative group
                          ${isActive
                            ? 'text-text_primary font-medium'
                            : 'text-text_secondary hover:text-text_primary'}`}
                        style={isActive ? {
                          background: 'var(--glass-elevated)',
                          borderLeft: '2px solid var(--accent-primary)',
                          paddingLeft: '10px',
                        } : undefined}
                        onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'var(--hover-glow)'; }}
                        onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
                        aria-current={isActive ? 'page' : undefined}
                      >
                        <Icon className="w-4 h-4 flex-shrink-0" style={{ opacity: isActive ? 1 : 0.65 }} />
                        <span className="text-[13px] truncate">{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>
      </aside>
    </>
  );
};

export default Sidebar;
