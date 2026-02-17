import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useSession } from '../contexts/SessionContext';
import { ShieldCheck, AlertTriangle, CheckCircle, XCircle, HelpCircle, Loader2 } from 'lucide-react';

interface VerifiedClaim {
    claim_text: string;
    original_text: string;
    status: 'Supported' | 'Weakly Supported' | 'Unsupported' | 'Contradicted';
    confidence: number;
    explanation: string;
    evidence_chunks: any[];
}

interface VerificationResult {
    verified_claims: VerifiedClaim[];
    summary: string;
    detailed_report: string;
}

const statusConfig: Record<string, { bg: string; border: string; text: string; icon: React.ElementType }> = {
    Supported: { bg: 'rgba(34,197,94,0.06)', border: 'rgba(34,197,94,0.15)', text: '#22C55E', icon: CheckCircle },
    'Weakly Supported': { bg: 'rgba(234,179,8,0.06)', border: 'rgba(234,179,8,0.15)', text: '#EAB308', icon: HelpCircle },
    Unsupported: { bg: 'rgba(239,68,68,0.06)', border: 'rgba(239,68,68,0.15)', text: '#EF4444', icon: XCircle },
    Contradicted: { bg: 'rgba(168,85,247,0.06)', border: 'rgba(168,85,247,0.15)', text: '#A855F7', icon: AlertTriangle },
};

const ClaimValidationPage: React.FC = () => {
    const [inputText, setInputText] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<VerificationResult | null>(null);
    const { token, user } = useAuth();
    const { sessionId } = useSession();

    const handleVerify = async () => {
        if (!inputText.trim()) return;
        setIsLoading(true);
        setResult(null);

        try {
            const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/verification/verify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    text: inputText,
                    user_id: user?.user_id || 'anonymous',
                    session_id: sessionId || 'default-session',
                }),
            });

            if (!response.ok) throw new Error('Verification failed');
            const data = await response.json();
            setResult(data);
        } catch (error) {
            console.error(error);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="p-4 sm:p-6 lg:p-8 overflow-y-auto h-full" style={{ background: 'var(--bg-primary)' }}>
            <div className="max-w-4xl mx-auto">
                {/* Page Header */}
                <div className="mb-6 sm:mb-8">
                    <div className="flex items-center gap-3 mb-2">
                        <div
                            className="w-10 h-10 sm:w-11 sm:h-11 rounded-glass-sm flex items-center justify-center flex-shrink-0"
                            style={{
                                background: 'var(--hover-glow)',
                                border: '1px solid var(--focus-ring)',
                            }}
                        >
                            <ShieldCheck className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />
                        </div>
                        <div>
                            <h1 className="text-xl sm:text-2xl font-semibold text-text_primary tracking-tight">Knowledge Verification</h1>
                            <p className="text-xs sm:text-sm text-text_muted">Verify claims against your uploaded documents</p>
                        </div>
                    </div>
                </div>

                {/* Input Area */}
                <div className="liquid-glass rounded-glass mb-6 sm:mb-8" style={{ padding: '16px' }}>
                    <div className="z-content relative">
                        <label className="block text-xs font-medium text-text_secondary mb-2">
                            Paste your answer or notes below for verification:
                        </label>
                        <textarea
                            className="input-field resize-none"
                            style={{ minHeight: '160px', fontSize: '14px', lineHeight: '1.7' }}
                            placeholder="E.g., Mitochondria is the powerhouse of the cell..."
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            aria-label="Text to verify"
                        />
                        <div className="mt-3 flex justify-end">
                            <button
                                onClick={handleVerify}
                                disabled={isLoading || !inputText.trim()}
                                className="btn-primary-liquid"
                                style={{ minHeight: '42px', padding: '0 24px', fontSize: '14px' }}
                                aria-label="Verify content"
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin z-content relative" />
                                        <span className="z-content relative">Verifying...</span>
                                    </>
                                ) : (
                                    <span className="z-content relative">Verify Content</span>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Results */}
                {result && (
                    <div className="space-y-5 sm:space-y-6 animate-fade-in">
                        {/* Summary card */}
                        <div
                            className="liquid-glass rounded-glass"
                            style={{ padding: '16px', borderLeft: '3px solid var(--accent-primary)' }}
                        >
                            <div className="z-content relative">
                                <h2 className="text-sm font-semibold text-text_primary mb-2">Summary</h2>
                                <p className="text-sm text-text_secondary leading-relaxed">{result.summary}</p>
                            </div>
                        </div>

                        {/* Claims */}
                        <div>
                            <h2 className="text-base sm:text-lg font-semibold text-text_primary mb-3 sm:mb-4">Verification Results</h2>
                            <div className="space-y-3">
                                {result.verified_claims.map((claim, index) => {
                                    const cfg = statusConfig[claim.status] || statusConfig.Unsupported;
                                    const StatusIcon = cfg.icon;
                                    return (
                                        <div
                                            key={index}
                                            className="rounded-glass overflow-hidden"
                                            style={{
                                                background: cfg.bg,
                                                border: `1px solid ${cfg.border}`,
                                                padding: '14px 16px',
                                            }}
                                        >
                                            <div className="flex items-start justify-between gap-3 mb-2">
                                                <div className="flex items-start gap-2.5 min-w-0">
                                                    <StatusIcon className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: cfg.text }} />
                                                    <h3 className="text-sm font-semibold text-text_primary leading-snug">{claim.claim_text}</h3>
                                                </div>
                                                <span
                                                    className="flex-shrink-0 text-[11px] font-bold px-2.5 py-1 rounded-pill whitespace-nowrap"
                                                    style={{
                                                        background: 'var(--glass-surface)',
                                                        color: cfg.text,
                                                        border: `1px solid ${cfg.border}`,
                                                    }}
                                                >
                                                    {claim.status} · {Math.round(claim.confidence * 100)}%
                                                </span>
                                            </div>
                                            <p className="text-xs text-text_secondary leading-relaxed ml-[26px] mb-2">{claim.explanation}</p>

                                            {claim.evidence_chunks && claim.evidence_chunks.length > 0 && (
                                                <div
                                                    className="ml-[26px] mt-2 pt-2"
                                                    style={{ borderTop: `1px solid ${cfg.border}` }}
                                                >
                                                    <p className="text-[11px] font-semibold uppercase tracking-wide mb-1" style={{ color: cfg.text, opacity: 0.7 }}>
                                                        Supporting Evidence:
                                                    </p>
                                                    <ul className="space-y-1">
                                                        {claim.evidence_chunks.slice(0, 2).map((chunk: any, i: number) => (
                                                            <li key={i} className="text-xs text-text_muted truncate">
                                                                • {chunk.text?.substring(0, 120)}...
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ClaimValidationPage;
