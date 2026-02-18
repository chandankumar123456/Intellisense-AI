import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

const AppLayout: React.FC = () => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const routerLocation = useLocation();

  const toggleSidebar = useCallback(() => {
    setIsSidebarCollapsed(prev => !prev);
  }, []);

  // Ctrl+B / Cmd+B
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') { e.preventDefault(); toggleSidebar(); }
    };
    document.addEventListener('keydown', h);
    return () => document.removeEventListener('keydown', h);
  }, [toggleSidebar]);

  return (
    <div className="flex h-screen" style={{ background: 'var(--bg-primary)' }}>
      <Sidebar isCollapsed={isSidebarCollapsed} onToggleCollapse={toggleSidebar} />
      <div
        className={`flex-1 flex flex-col min-w-0 ${isSidebarCollapsed ? 'lg:ml-0' : 'lg:ml-sidebar'}`}
        style={{
          transition: 'margin 400ms cubic-bezier(0.2, 0.8, 0.2, 1)',
        }}
      >
        <Header isCollapsed={isSidebarCollapsed} onToggleSidebar={toggleSidebar} />
        <main className="flex-1 overflow-hidden relative">
          <div
            key={routerLocation.pathname}
            className="h-full w-full animate-fade-in"
          >
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
