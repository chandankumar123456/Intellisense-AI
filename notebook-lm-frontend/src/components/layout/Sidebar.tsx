import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Home,
  MessageSquare,
  Clock,
  Globe,
  Youtube,
  Settings,
  Menu,
  X,
} from 'lucide-react';

interface NavItem {
  icon: React.ElementType;
  label: string;
  path: string;
}

const navItems: NavItem[] = [
  { icon: Home, label: 'Home', path: '/app/home' },
  { icon: MessageSquare, label: 'Chat', path: '/app/chat' },
  { icon: Clock, label: 'History', path: '/app/history' },
  { icon: Globe, label: 'Web', path: '/app/web' },
  { icon: Youtube, label: 'YouTube', path: '/app/youtube' },
  { icon: Settings, label: 'Settings', path: '/app/settings' },
];

const Sidebar: React.FC = () => {
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileOpen(false);
  }, [location.pathname]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setIsMobileOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  const toggleMobile = () => {
    setIsMobileOpen(!isMobileOpen);
  };

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={toggleMobile}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-white rounded-lg shadow-md border border-border"
        aria-label="Toggle menu"
      >
        {isMobileOpen ? (
          <X className="w-6 h-6 text-text_primary" />
        ) : (
          <Menu className="w-6 h-6 text-text_primary" />
        )}
      </button>

      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={toggleMobile}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          ${isCollapsed ? 'w-16' : 'w-sidebar'} 
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          bg-white border-r border-border h-screen fixed left-0 top-0 overflow-y-auto z-40
          transition-all duration-300 ease-in-out
        `}
      >
        <div className="p-4">
          <div className="flex items-center justify-between mb-8">
            <Link
              to="/app/home"
              className={`block ${isCollapsed ? 'mx-auto' : ''}`}
            >
              <h2
                className={`text-2xl font-bold text-primary ${
                  isCollapsed ? 'text-xl' : ''
                }`}
              >
                {isCollapsed ? 'NL' : 'Notebook LM'}
              </h2>
            </Link>
            {!isCollapsed && (
              <button
                onClick={toggleCollapse}
                className="hidden lg:block p-1 text-text_secondary hover:text-text_primary"
                aria-label="Collapse sidebar"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-lg transition-colors duration-200
                    ${isCollapsed ? 'justify-center' : ''}
                    ${
                      isActive
                        ? 'bg-blue-50 text-blue-600 font-medium'
                        : 'text-text_secondary hover:bg-surface hover:text-text_primary'
                    }
                  `}
                  aria-current={isActive ? 'page' : undefined}
                  title={isCollapsed ? item.label : undefined}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                  {!isCollapsed && <span>{item.label}</span>}
                </Link>
              );
            })}
          </nav>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
