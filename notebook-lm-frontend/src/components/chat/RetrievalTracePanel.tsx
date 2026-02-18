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
          {/* Trace ID */}
          {trace.trace_id && (
            <div className="text-[10px] text-text_muted font-mono mb-2 flex justify-between">
              <span>Trace ID: {trace.trace_id}</span>
              {trace.secondary_retry_triggered && (
                <span className="text-warning font-bold flex items-center gap-1">
                  <Zap className="w-3 h-3" /> Retry Triggered
                </span>
              )}
            </div>
          )}

          {/* Validation Status */}
          {trace.retrieval_validation && (
            <div className={`p-3 rounded-glass-sm bg-opacity-10 border border-border-subtle ${trace.retrieval_validation.is_valid ? 'bg-success/10' : 'bg-warning/10'}`}>
              <div className="flex items-center justify-between mb-1">
                <span className={`text-xs font-semibold ${trace.retrieval_validation.is_valid ? 'text-text_success' : 'text-text_warning'}`}>
                  {trace.retrieval_validation.is_valid ? 'Validation Passed' : 'Validation Failed'}
                </span>
                <span className="text-[10px] text-text_muted uppercase tracking-wider">
                  Top Score: {trace.retrieval_validation.top_score?.toFixed(3)}
                </span>
              </div>
              <p className="text-xs text-text_secondary italic">{trace.retrieval_validation.reason}</p>
            </div>
          )}

          {/* Results Grid */}
          {trace.results && (
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(trace.results).map(([key, data]: [string, any]) => {
                if (!data || key === 'retry_count') return null;
                return (
                  <div key={key} className="p-2 rounded-glass-sm border border-border-subtle bg-bg-secondary">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Zap className="w-3 h-3 text-accent-primary" />
                      <span className="text-xs font-medium capitalize text-text_primary">
                        {key.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-text_muted">
                      <span>{data.count || 0} chunks</span>
                      <span className={`px-1.5 py-0.5 rounded-full ${data.status === 'success' ? 'bg-success/20 text-success' : 'bg-bg-tertiary'}`}>
                        {data.status}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Top Chunks Viewer */}
          {trace.top_chunks && trace.top_chunks.length > 0 && (
            <div className="mt-4">
              <h4 className="text-xs font-semibold text-text_secondary mb-2">Top Chunks</h4>
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
                {trace.top_chunks.map((chunk: any, i: number) => (
                  <div key={i} className="p-2 rounded-glass-sm bg-bg-secondary border border-border-subtle hover:bg-bg-tertiary transition-colors">
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-[10px] font-mono text-text_muted truncate max-w-[120px]" title={chunk.chunk_id}>
                        {chunk.chunk_id.substring(0, 8)}...
                      </span>
                      <div className="flex gap-1.5">
                        <span className="text-[9px] px-1 rounded-full bg-primary/10 text-primary">
                          {chunk.rerank_score?.toFixed(3)}
                        </span>
                        {chunk.definition_score > 0 && (
                          <span className="text-[9px] px-1 rounded-full bg-info/10 text-info" title="Definition Score">
                            Def: {chunk.definition_score?.toFixed(2)}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-[10px] text-text_secondary mb-1 flex gap-2">
                      <span className="capitalize">{chunk.source_type}</span>
                      {chunk.section_type && <span className="text-text_muted">• {chunk.section_type}</span>}
                    </div>
                    <p className="text-[10px] text-text_muted leading-snug line-clamp-2">
                      {chunk.text_preview}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RetrievalTracePanel;
