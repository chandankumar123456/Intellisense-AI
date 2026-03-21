import React, { useState, useRef, useEffect } from 'react';
import { Send, Mic, MicOff } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string, options?: any) => void;
  isLoading?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, isLoading = false }) => {
  const [message, setMessage] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 140) + 'px';
    }
  }, [message]);

  const handleSubmit = () => {
    if (!message.trim() || isLoading) return;
    onSendMessage(message.trim());
    setMessage('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
  };

  const toggleVoice = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) return;
    if (isListening) { recognitionRef.current?.stop(); setIsListening(false); return; }
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const rec = new SR(); rec.continuous = false; rec.interimResults = false;
    rec.onresult = (e: any) => { setMessage(prev => prev + e.results[0][0].transcript); setIsListening(false); };
    rec.onerror = () => setIsListening(false);
    rec.onend = () => setIsListening(false);
    recognitionRef.current = rec; rec.start(); setIsListening(true);
  };

  const hasSR = typeof window !== 'undefined' && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window);
  const canSend = message.trim() && !isLoading;

  return (
    <div
      className="rounded-glass-lg transition-all duration-normal"
      style={{
        background: 'var(--glass-elevated)',
        border: `1px solid ${isFocused ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
        boxShadow: isFocused
          ? '0 0 0 2px var(--focus-ring), 0 2px 8px var(--glass-shadow)'
          : '0 1px 3px var(--glass-shadow)',
        padding: '4px',
      }}
    >
      <div className="flex items-end gap-1.5" style={{ minHeight: '40px' }}>
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Ask anything about your documents..."
          className="flex-1 bg-transparent border-none outline-none resize-none text-text_primary placeholder-text_muted py-2.5 px-3 max-h-36 leading-relaxed"
          style={{ fontSize: '14px', minHeight: '40px' }}
          rows={1}
          disabled={isLoading}
          aria-label="Chat message input"
        />
        <div className="flex items-center gap-1 pb-1 pr-1 flex-shrink-0">
          {hasSR && (
            <button
              onClick={toggleVoice}
              className="rounded-glass-sm transition-all duration-fast active:scale-[0.90] flex items-center justify-center"
              style={{
                width: '36px', height: '36px',
                background: isListening ? 'var(--active-glow)' : 'transparent',
                color: isListening ? 'var(--text-primary)' : 'var(--text-muted)',
              }}
              onMouseEnter={(e) => { if (!isListening) e.currentTarget.style.color = 'var(--text-secondary)'; }}
              onMouseLeave={(e) => { if (!isListening) e.currentTarget.style.color = 'var(--text-muted)'; }}
              aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
            >
              {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
          )}
          <button
            onClick={handleSubmit}
            disabled={!canSend}
            className="rounded-glass-sm transition-all duration-fast active:scale-[0.90] flex items-center justify-center"
            style={{
              width: '36px', height: '36px',
              background: canSend ? 'var(--accent-primary)' : 'transparent',
              color: canSend ? 'var(--text-inverse)' : 'var(--text-muted)',
              opacity: (!message.trim() || isLoading) ? 0.5 : 1,
              border: canSend ? 'none' : '1px solid var(--border-subtle)',
            }}
            aria-label="Send message"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInput;
