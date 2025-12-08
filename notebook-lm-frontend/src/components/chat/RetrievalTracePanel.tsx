import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { RetrievalTrace } from '../../types/api.types';

interface RetrievalTracePanelProps {
  trace: RetrievalTrace | null;
  confidence?: number;
  latency?: number;
}

const RetrievalTracePanel: React.FC<RetrievalTracePanelProps> = ({
  trace,
  confidence,
  latency,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!trace) {
    return null;
  }

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.7) return 'text-success';
    if (conf >= 0.4) return 'text-warning';
    return 'text-error';
  };

  const getConfidenceLabel = (conf: number) => {
    if (conf >= 0.7) return 'High';
    if (conf >= 0.4) return 'Medium';
    return 'Low';
  };

  return (
    <div className="border border-border rounded-lg bg-surface mt-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
        aria-expanded={isExpanded}
        aria-label="Toggle retrieval trace details"
      >
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-text_primary">Retrieval Trace</span>
          {confidence !== undefined && (
            <span className={`text-sm font-medium ${getConfidenceColor(confidence)}`}>
              Confidence: {getConfidenceLabel(confidence)} ({Math.round(confidence * 100)}%)
            </span>
          )}
          {latency && (
            <span className="text-xs text-text_secondary">Latency: {latency}ms</span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-text_secondary" />
        ) : (
          <ChevronDown className="w-4 h-4 text-text_secondary" />
        )}
      </button>

      {isExpanded && (
        <div className="p-4 border-t border-border space-y-3">
          <div>
            <p className="text-xs font-medium text-text_secondary mb-1">Trace ID</p>
            <p className="text-sm text-text_primary font-mono">{trace.trace_id}</p>
          </div>

          <div>
            <p className="text-xs font-medium text-text_secondary mb-1">Query</p>
            <p className="text-sm text-text_primary">{trace.query}</p>
          </div>

          <div>
            <p className="text-xs font-medium text-text_secondary mb-2">Retrievers Used</p>
            <div className="flex flex-wrap gap-2">
              {trace.retrievers_used.map((retriever, index) => (
                <span
                  key={index}
                  className="px-2 py-1 bg-primary/10 text-primary text-xs rounded"
                >
                  {retriever}
                </span>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {trace.results.vector && (
              <div>
                <p className="text-xs font-medium text-text_secondary mb-1">Vector Retrieval</p>
                <p className="text-sm text-text_primary">
                  {trace.results.vector.count}/{trace.results.vector.top_k} top-k
                </p>
                <p className="text-xs text-text_secondary">{trace.results.vector.status}</p>
              </div>
            )}

            {trace.results.keyword && (
              <div>
                <p className="text-xs font-medium text-text_secondary mb-1">Keyword Retrieval</p>
                <p className="text-sm text-text_primary">
                  {trace.results.keyword.count}/{trace.results.keyword.top_k} top-k
                </p>
                <p className="text-xs text-text_secondary">{trace.results.keyword.status}</p>
              </div>
            )}

            {trace.results.web && (
              <div>
                <p className="text-xs font-medium text-text_secondary mb-1">Web Retrieval</p>
                <p className="text-sm text-text_primary">
                  {trace.results.web.count}/{trace.results.web.top_k} top-k
                </p>
                <p className="text-xs text-text_secondary">{trace.results.web.status}</p>
              </div>
            )}

            {trace.results.youtube && (
              <div>
                <p className="text-xs font-medium text-text_secondary mb-1">YouTube Retrieval</p>
                <p className="text-sm text-text_primary">
                  {trace.results.youtube.count}/{trace.results.youtube.top_k} top-k
                </p>
                <p className="text-xs text-text_secondary">{trace.results.youtube.status}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default RetrievalTracePanel;
