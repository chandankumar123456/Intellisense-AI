import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight, oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, ExternalLink, Clock, Activity } from 'lucide-react';
import RetrievalTracePanel from './RetrievalTracePanel';
import { useTheme } from '../../contexts/ThemeContext';

interface ChatMessageProps {
  message: {
    id?: string;
    role: 'user' | 'assistant';
    content: string;
    citations?: any[];
    confidence?: number;
    latency?: number;
    retrieval_trace?: any;
  };
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const { theme } = useTheme();
  const isUser = message.role === 'user';
  const [copied, setCopied] = React.useState(false);
  const hasRefs = !isUser && (message.citations?.length || message.retrieval_trace);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-message-in`}>
      <div className={`relative group ${isUser ? 'message-user' : `message-assistant ${hasRefs ? 'has-references' : ''}`}`}>
        {/* Content */}
        <div className="z-content relative">
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="text-sm leading-relaxed mb-2 last:mb-0">{children}</p>,
              strong: ({ children }) => <strong className="font-semibold text-text_primary">{children}</strong>,
              code: ({ className, children, ...props }: any) => {
                const match = /language-(\w+)/.exec(className || '');
                const lang = match?.[1];
                if (lang) {
                  return (
                    <div className="my-3 rounded-glass-sm overflow-hidden" style={{ border: '1px solid var(--border-subtle)' }}>
                      <div className="flex items-center justify-between px-3 py-1.5" style={{ background: 'var(--bg-secondary)' }}>
                        <span className="text-xs text-text_muted">{lang}</span>
                        <button
                          onClick={handleCopy}
                          className="text-text_muted hover:text-text_primary transition-colors duration-fast p-0.5"
                          aria-label="Copy code"
                        >
                          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        </button>
                      </div>
                      <SyntaxHighlighter
                        style={theme === 'dark' ? oneDark : oneLight}
                        language={lang}
                        PreTag="div"
                        customStyle={{ margin: 0, padding: '12px 16px', background: 'transparent', fontSize: '12px' }}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    </div>
                  );
                }
                return (
                  <code className="px-1.5 py-0.5 rounded-md text-xs font-mono" style={{ background: 'var(--hover-glow)', color: 'var(--accent-primary)' }}>
                    {children}
                  </code>
                );
              },
              ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-2 text-sm">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-2 text-sm">{children}</ol>,
              a: ({ href, children }) => (
                <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline inline-flex items-center gap-0.5">
                  {children} <ExternalLink className="w-3 h-3 inline" />
                </a>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-3 pl-3 my-2 italic text-text_secondary" style={{ borderColor: 'var(--accent-secondary)' }}>
                  {children}
                </blockquote>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>

          {/* Citations */}
          {!isUser && message.citations && message.citations.length > 0 && (
            <div className="mt-3 pt-3 space-y-1.5" style={{ borderTop: '1px solid var(--border-subtle)' }}>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text_muted">Sources</span>
              <div className="flex flex-wrap gap-1.5">
                {message.citations.map((citation: any, idx: number) => (
                  <a
                    key={idx}
                    href={citation.url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-xs transition-all duration-fast"
                    style={{
                      background: 'var(--hover-glow)',
                      border: '1px solid var(--border-subtle)',
                      color: 'var(--accent-primary)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = '0 0 12px var(--hover-glow)';
                      e.currentTarget.style.transform = 'translateY(-1px)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'none';
                      e.currentTarget.style.transform = 'translateY(0)';
                    }}
                  >
                    <span className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold" style={{ background: 'var(--accent-primary)', color: 'var(--text-inverse)' }}>
                      {idx + 1}
                    </span>
                    <span className="truncate max-w-[120px]">{citation.title || citation.source || `Source ${idx + 1}`}</span>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          {!isUser && (message.confidence !== undefined || message.latency) && (
            <div className="flex items-center gap-4 mt-3 pt-2" style={{ borderTop: '1px solid var(--border-subtle)' }}>
              {message.confidence !== undefined && (
                <div className="flex items-center gap-1.5 text-[10px] text-text_muted">
                  <Activity className="w-3 h-3" />
                  <span>{Math.round(message.confidence * 100)}% confidence</span>
                </div>
              )}
              {message.latency && (
                <div className="flex items-center gap-1 text-[10px] text-text_muted">
                  <Clock className="w-3 h-3" />
                  <span>{message.latency}ms</span>
                </div>
              )}
            </div>
          )}

          {/* Copy button on hover */}
          {!isUser && (
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 p-1.5 rounded-glass-sm opacity-0 group-hover:opacity-100 transition-all duration-fast"
              style={{ background: 'var(--glass-surface)', border: '1px solid var(--border-subtle)' }}
              aria-label="Copy message"
            >
              {copied ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3 text-text_muted" />}
            </button>
          )}
        </div>

        {/* Retrieval trace */}
        {!isUser && message.retrieval_trace && (
          <div className="z-content relative">
            <RetrievalTracePanel
              trace={message.retrieval_trace}
              confidence={message.confidence}
              latency={message.latency}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
