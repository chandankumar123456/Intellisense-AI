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
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + 'px';
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

  return (
    <div
      className="liquid-glass rounded-glass-lg transition-all duration-normal"
      style={{
        padding: '6px',
        boxShadow: isFocused
          ? '0 0 0 3px var(--focus-ring), 0 8px 32px var(--hover-glow)'
          : '0 4px 16px var(--glass-shadow), inset 0 2px 4px rgba(0,0,0,0.02)',
        transform: isFocused ? 'scale(1.003)' : 'scale(1)',
      }}
    >
      <div className="flex items-end gap-2 z-content relative" style={{ minHeight: '44px' }}>
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Ask anything about your documents..."
          className="flex-1 bg-transparent border-none outline-none resize-none text-text_primary placeholder-text_muted py-3 px-3 sm:px-4 max-h-40 leading-relaxed"
          style={{ fontSize: '14px', minHeight: '44px' }}
          rows={1}
          disabled={isLoading}
          aria-label="Chat message input"
        />
        <div className="flex items-center gap-1.5 pb-1.5 pr-1 flex-shrink-0">
          {hasSR && (
            <button
              onClick={toggleVoice}
              className="rounded-full transition-all duration-fast active:scale-[0.88] flex items-center justify-center"
              style={{
                width: '40px', height: '40px',
                background: isListening ? 'var(--active-glow)' : 'transparent',
                color: isListening ? 'var(--accent-secondary)' : 'var(--text-muted)',
              }}
              onMouseEnter={(e) => { if (!isListening) e.currentTarget.style.background = 'var(--hover-glow)'; }}
              onMouseLeave={(e) => { if (!isListening) e.currentTarget.style.background = 'transparent'; }}
              aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
            >
              {isListening ? <MicOff className="w-[18px] h-[18px]" /> : <Mic className="w-[18px] h-[18px]" />}
            </button>
          )}
          <button
            onClick={handleSubmit}
            disabled={!message.trim() || isLoading}
            className="rounded-glass-sm transition-all duration-fast active:scale-[0.88] flex items-center justify-center"
            style={{
              width: '40px', height: '40px',
              background: message.trim()
                ? 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))'
                : 'var(--hover-glow)',
              color: message.trim() ? '#FFFFFF' : 'var(--text-muted)',
              boxShadow: message.trim() ? '0 4px 16px var(--hover-glow)' : 'none',
              opacity: (!message.trim() || isLoading) ? 0.6 : 1,
            }}
            aria-label="Send message"
          >
            <Send className="w-[18px] h-[18px]" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInput;
