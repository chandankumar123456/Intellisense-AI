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
        <ReactMarkdown
          components={{
            p: ({ children }) => <p className="text-sm leading-relaxed mb-2 last:mb-0">{children}</p>,
            strong: ({ children }) => (
              <strong className="font-semibold" style={{ color: isUser ? 'inherit' : 'var(--text-primary)' }}>
                {children}
              </strong>
            ),
            em: ({ children }) => <em className="italic">{children}</em>,
            h1: ({ children }) => <h1 className="text-base font-bold mb-2 mt-3 first:mt-0" style={{ color: 'var(--text-primary)' }}>{children}</h1>,
            h2: ({ children }) => <h2 className="text-sm font-semibold mb-1.5 mt-2.5 first:mt-0" style={{ color: 'var(--text-primary)' }}>{children}</h2>,
            h3: ({ children }) => <h3 className="text-sm font-semibold mb-1 mt-2 first:mt-0" style={{ color: 'var(--text-secondary)' }}>{children}</h3>,
            code: ({ className, children, ...props }: any) => {
              const match = /language-(\w+)/.exec(className || '');
              const lang = match?.[1];
              if (lang) {
                return (
                  <div className="my-3 rounded-glass-sm overflow-hidden" style={{ border: '1px solid var(--border-subtle)' }}>
                    <div
                      className="flex items-center justify-between px-3 py-1.5"
                      style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-subtle)' }}
                    >
                      <span className="label-sm">{lang}</span>
                      <button
                        onClick={handleCopy}
                        className="text-text_muted hover:text-text_primary transition-colors duration-fast p-0.5 rounded"
                        aria-label="Copy code"
                      >
                        {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                      </button>
                    </div>
                    <SyntaxHighlighter
                      style={theme === 'dark' ? oneDark : oneLight}
                      language={lang}
                      PreTag="div"
                      customStyle={{
                        margin: 0,
                        padding: '10px 14px',
                        background: 'transparent',
                        fontSize: '12px',
                        lineHeight: '1.6',
                      }}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  </div>
                );
              }
              return (
                <code
                  className="px-1 py-0.5 rounded text-xs font-mono"
                  style={{
                    background: isUser ? 'rgba(255,255,255,0.15)' : 'var(--bg-secondary)',
                    color: isUser ? 'inherit' : 'var(--text-primary)',
                    border: isUser ? 'none' : '1px solid var(--border-subtle)',
                  }}
                >
                  {children}
                </code>
              );
            },
            ul: ({ children }) => <ul className="list-disc list-outside pl-4 space-y-1 mb-2 text-sm">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal list-outside pl-4 space-y-1 mb-2 text-sm">{children}</ol>,
            li: ({ children }) => <li className="leading-relaxed">{children}</li>,
            a: ({ href, children }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:underline inline-flex items-center gap-0.5"
                style={{ color: isUser ? 'inherit' : 'var(--accent-primary)', textDecorationColor: 'var(--text-muted)' }}
              >
                {children}
                <ExternalLink className="w-2.5 h-2.5 inline flex-shrink-0" />
              </a>
            ),
            blockquote: ({ children }) => (
              <blockquote
                className="pl-3 my-2 italic text-sm"
                style={{
                  borderLeft: '2px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                }}
              >
                {children}
              </blockquote>
            ),
            table: ({ children }) => (
              <div className="overflow-x-auto my-3">
                <table className="w-full text-xs border-collapse">{children}</table>
              </div>
            ),
            thead: ({ children }) => (
              <thead style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-subtle)' }}>
                {children}
              </thead>
            ),
            th: ({ children }) => (
              <th className="text-left px-3 py-1.5 font-semibold text-text_secondary">{children}</th>
            ),
            td: ({ children }) => (
              <td className="px-3 py-1.5 text-text_primary" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                {children}
              </td>
            ),
          }}
        >
          {message.content}
        </ReactMarkdown>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--border-subtle)' }}>
            <span className="label-sm block mb-2">Sources</span>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((citation: any, idx: number) => (
                <a
                  key={idx}
                  href={citation.url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-all duration-fast"
                  style={{
                    background: 'var(--glass-surface)',
                    border: '1px solid var(--border-subtle)',
                    color: 'var(--text-secondary)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent-primary)';
                    e.currentTarget.style.color = 'var(--text-primary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border-subtle)';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }}
                >
                  <span
                    className="w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] font-bold flex-shrink-0"
                    style={{ background: 'var(--border-subtle)', color: 'var(--text-muted)' }}
                  >
                    {idx + 1}
                  </span>
                  <span className="truncate max-w-[110px]">{citation.title || citation.source || `Source ${idx + 1}`}</span>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Metadata */}
        {!isUser && (message.confidence !== undefined || message.latency) && (
          <div className="flex items-center gap-4 mt-2.5 pt-2" style={{ borderTop: '1px solid var(--border-subtle)' }}>
            {message.confidence !== undefined && (
              <div className="flex items-center gap-1 text-[10px] text-text_muted">
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
            className="absolute top-2 right-2 p-1 rounded opacity-0 group-hover:opacity-100 transition-all duration-fast"
            style={{
              background: 'var(--glass-surface)',
              border: '1px solid var(--border-subtle)',
            }}
            aria-label="Copy message"
          >
            {copied ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3 text-text_muted" />}
          </button>
        )}

        {/* Retrieval trace */}
        {!isUser && message.retrieval_trace && (
          <RetrievalTracePanel
            trace={message.retrieval_trace}
            confidence={message.confidence}
            latency={message.latency}
          />
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
