import React from 'react';
import { Link } from 'react-router-dom';
import { MessageSquare, FileText, Globe, Youtube, ArrowRight, Zap, Database, Activity } from 'lucide-react';

const HomePage: React.FC = () => {
  const quickActions = [
    {
      icon: MessageSquare,
      title: 'Chat',
      desc: 'Ask questions from your knowledge base with AI-powered retrieval',
      path: '/app/chat',
      variant: 'featured',
    },
    {
      icon: Globe,
      title: 'Web Sources',
      desc: 'Manage and search web sources',
      path: '/app/web',
      variant: 'default',
    },
    {
      icon: Youtube,
      title: 'YouTube',
      desc: 'Index and search video content',
      path: '/app/youtube',
      variant: 'default',
    },
    {
      icon: FileText,
      title: 'History',
      desc: 'View previous conversations',
      path: '/app/history',
      variant: 'compact',
    },
  ];

  const stats = [
    { label: 'Sources Indexed', value: '—', icon: Database },
    { label: 'Avg. Confidence', value: '—', icon: Activity },
    { label: 'Sessions', value: '—', icon: Zap },
  ];

  return (
    <div className="p-5 sm:p-7 lg:p-8 overflow-y-auto h-full" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-3xl mx-auto">

        {/* Header — strong primary heading */}
        <div className="mb-8 animate-fade-in-up">
          <h1 className="heading-xl mb-1">Welcome back</h1>
          <p className="text-sm text-text_secondary">IntelliSense AI · Agentic RAG</p>
        </div>

        {/* Stats row — metric cards */}
        <div className="grid grid-cols-3 gap-3 mb-8">
          {stats.map(({ label, value, icon: Icon }) => (
            <div key={label} className="card-metric">
              <div className="flex items-start justify-between mb-2">
                <span className="label-sm">{label}</span>
                <Icon className="w-3.5 h-3.5 text-text_muted flex-shrink-0 mt-0.5" />
              </div>
              <div className="text-xl font-bold text-text_primary tracking-tight" style={{ fontVariantNumeric: 'tabular-nums' }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Quick actions — varied density */}
        <div className="mb-8">
          <h2 className="heading-md mb-4">Quick Actions</h2>

          {/* Featured action — gets more space */}
          <div className="mb-3">
            <Link to={quickActions[0].path} className="group block card-featured animate-scale-in">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2.5 mb-3">
                    <div
                      className="w-9 h-9 rounded-glass-sm flex items-center justify-center flex-shrink-0"
                      style={{ background: 'var(--accent-primary)' }}
                    >
                      <MessageSquare className="w-4 h-4" style={{ color: 'var(--text-inverse)' }} />
                    </div>
                    <h3 className="heading-md">{quickActions[0].title}</h3>
                  </div>
                  <p className="text-sm text-text_secondary leading-relaxed max-w-sm">{quickActions[0].desc}</p>
                </div>
                <ArrowRight className="w-4 h-4 text-text_muted opacity-0 group-hover:opacity-100 transition-all duration-fast mt-1 group-hover:translate-x-1 flex-shrink-0 ml-4" />
              </div>
            </Link>
          </div>

          {/* Standard actions — equal grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            {quickActions.slice(1, 3).map(({ icon: Icon, title, desc, path }, index) => (
              <Link
                key={path}
                to={path}
                className="group card animate-scale-in"
                style={{ animationDelay: `${(index + 1) * 60}ms` }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className="w-4 h-4 text-text_secondary flex-shrink-0" />
                      <h3 className="text-sm font-semibold text-text_primary">{title}</h3>
                    </div>
                    <p className="text-xs text-text_secondary leading-relaxed">{desc}</p>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-text_muted opacity-0 group-hover:opacity-100 transition-all duration-fast group-hover:translate-x-1 flex-shrink-0 ml-3 mt-0.5" />
                </div>
              </Link>
            ))}
          </div>

          {/* Compact action — minimal */}
          <Link
            to={quickActions[3].path}
            className="group card-compact flex items-center justify-between animate-scale-in"
            style={{ animationDelay: '180ms' }}
          >
            <div className="flex items-center gap-2.5">
              <FileText className="w-3.5 h-3.5 text-text_muted flex-shrink-0" />
              <div>
                <span className="text-sm font-medium text-text_secondary group-hover:text-text_primary transition-colors duration-fast">
                  {quickActions[3].title}
                </span>
                <span className="text-xs text-text_muted ml-2">{quickActions[3].desc}</span>
              </div>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-text_muted opacity-0 group-hover:opacity-100 transition-all duration-fast group-hover:translate-x-1 flex-shrink-0" />
          </Link>
        </div>

        {/* CTA */}
        <Link to="/app/chat">
          <button className="btn-primary-liquid w-full sm:w-auto" style={{ minHeight: '44px', padding: '10px 28px', fontSize: '14px' }}>
            Start Chatting
          </button>
        </Link>
      </div>
    </div>
  );
};

export default HomePage;
