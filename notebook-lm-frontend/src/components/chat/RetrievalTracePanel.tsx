import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Activity, Zap, Clock } from 'lucide-react';

interface RetrievalTracePanelProps {
  trace: any;
  confidence?: number;
  latency?: number;
}

const RetrievalTracePanel: React.FC<RetrievalTracePanelProps> = ({ trace, confidence, latency }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!trace) return null;

  return (
    <div
      className="rounded-glass mt-3 overflow-hidden transition-all duration-normal liquid-glass"
      style={{ boxShadow: '0 4px 12px var(--glass-shadow)' }}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 z-content relative transition-all duration-fast"
        onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--hover-glow)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
        aria-expanded={isExpanded}
        aria-label="Toggle retrieval trace details"
      >
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-primary" />
          <span className="text-xs font-medium text-text_secondary">Retrieval Trace</span>
        </div>
        <div className="flex items-center gap-3">
          {confidence !== undefined && (
            <div className="flex items-center gap-1.5">
              <div className={`w-1.5 h-1.5 rounded-full ${confidence > 0.7 ? 'bg-success' : confidence > 0.4 ? 'bg-warning' : 'bg-error'
                }`} />
              <span className="text-[10px] text-text_muted">{Math.round(confidence * 100)}%</span>
            </div>
          )}
          {latency && (
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-text_muted" />
              <span className="text-[10px] text-text_muted">{latency}ms</span>
            </div>
          )}
          {isExpanded ? <ChevronUp className="w-3.5 h-3.5 text-text_muted" /> : <ChevronDown className="w-3.5 h-3.5 text-text_muted" />}
        </div>
      </button>

      {isExpanded && (
        <div className="p-4 space-y-3 animate-fade-in z-content relative" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          {trace.retrievers && Object.entries(trace.retrievers).map(([name, data]: [string, any]) => (
            <div key={name} className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-text_secondary flex items-center gap-1.5">
                  <Zap className="w-3 h-3 text-primary" />{name}
                </span>
                {data.num_results !== undefined && (
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-pill" style={{ background: 'var(--hover-glow)', color: 'var(--accent-primary)' }}>
                    {data.num_results} results
                  </span>
                )}
              </div>
              {data.results?.length > 0 && (
                <div className="grid gap-1.5 ml-6">
                  {data.results.map((result: any, idx: number) => (
                    <div key={idx} className="px-3 py-2 rounded-glass-sm text-xs" style={{ background: 'var(--glass-surface)', border: '1px solid var(--border-subtle)' }}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-text_secondary truncate">{result.source || `Result ${idx + 1}`}</span>
                        {result.score !== undefined && <span className="text-text_muted ml-2 flex-shrink-0">{(result.score * 100).toFixed(0)}%</span>}
                      </div>
                      {result.content && <p className="text-text_muted truncate">{result.content.substring(0, 100)}...</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RetrievalTracePanel;
