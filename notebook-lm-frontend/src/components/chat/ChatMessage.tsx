import React, { useState } from 'react';
import { Copy, Check, ExternalLink } from 'lucide-react';
import { Message } from '../../types/chat.types';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTime = (time: any) => {
    if (!time) return "";
  
    const date = new Date(time);
  
    if (isNaN(date.getTime())) {
      return "";
    }
  
    return new Intl.DateTimeFormat("en-US", {
      hour: "numeric",
      minute: "2-digit",
    }).format(date);
  };
  

  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-4 animate-fade-in-up">
        <div className="message-user max-w-[80%]">
          <p className="text-white whitespace-pre-wrap break-words">{message.content}</p>
          <p className="text-xs text-blue-100 mt-1">{formatTime(message.timestamp)}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-4 animate-fade-in-up">
      <div className="message-assistant max-w-[80%]">
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown
            components={{
              code({ node, inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || '');
                const language = match ? match[1] : '';
                return !inline && language ? (
                  <SyntaxHighlighter
                    style={vscDarkPlus}
                    language={language}
                    PreTag="div"
                    className="rounded-lg"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {message.metadata?.citations && message.metadata.citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border">
            <p className="text-xs font-medium text-text_secondary mb-2">Citations:</p>
            <div className="flex flex-wrap gap-2">
              {message.metadata.citations.map((citation, index) => (
                <a
                  key={index}
                  href={citation}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:text-primary_dark flex items-center gap-1 underline"
                >
                  <ExternalLink className="w-3 h-3" />
                  Source {index + 1}
                </a>
              ))}
            </div>
          </div>
        )}

        {message.metadata?.used_chunk_ids && message.metadata.used_chunk_ids.length > 0 && (
          <div className="mt-3 pt-3 border-t border-border">
            <p className="text-xs font-medium text-text_secondary mb-2">Chunks Used:</p>
            <div className="flex flex-wrap gap-2">
              {message.metadata.used_chunk_ids.map((chunkId, index) => (
                <span
                  key={index}
                  className="text-xs text-primary flex items-center gap-1"
                >
                  <ExternalLink className="w-3 h-3" />
                  Chunk {index + 1}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
          <div className="flex items-center gap-4 text-xs text-text_secondary">
            {message.metadata?.confidence !== undefined && (
              <span>
                Confidence: {Math.round(message.metadata.confidence * 100)}%
              </span>
            )}
            {message.metadata?.latency_ms && (
              <span>Latency: {message.metadata.latency_ms}ms</span>
            )}
          </div>
          <button
            onClick={handleCopy}
            className="text-text_secondary hover:text-text_primary transition-colors"
            aria-label="Copy message"
          >
            {copied ? (
              <Check className="w-4 h-4 text-success" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>

        <p className="text-xs text-text_secondary mt-1">{formatTime(message.timestamp)}</p>
      </div>
    </div>
  );
};

export default ChatMessage;
