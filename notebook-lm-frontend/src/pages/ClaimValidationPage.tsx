import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useSession } from '../contexts/SessionContext';

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
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    text: inputText,
                    user_id: user?.user_id || 'anonymous',
                    session_id: sessionId || 'default-session'
                })
            });

            if (!response.ok) {
                throw new Error('Verification failed');
            }

            const data = await response.json();
            setResult(data);
        } catch (error) {
            console.error(error);
            alert('Failed to verify claims. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'Supported': return 'bg-green-100 text-green-800 border-green-200';
            case 'Weakly Supported': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'Unsupported': return 'bg-red-100 text-red-800 border-red-200';
            case 'Contradicted': return 'bg-purple-100 text-purple-800 border-purple-200';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="container mx-auto px-4 py-8 max-w-4xl">
            <h1 className="text-3xl font-bold mb-6 text-gray-800">EviLearn: Knowledge Verification</h1>

            <div className="mb-8">
                <label className="block text-gray-700 text-sm font-bold mb-2">
                    Paste your answer or notes below for verification:
                </label>
                <textarea
                    className="w-full h-48 p-4 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                    placeholder="E.g., Mitochondria is the powerhouse of the cell..."
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                />
                <div className="mt-4 flex justify-end">
                    <button
                        onClick={handleVerify}
                        disabled={isLoading || !inputText.trim()}
                        className={`px-6 py-2 rounded-lg text-white font-semibold transition-colors ${isLoading || !inputText.trim()
                            ? 'bg-gray-400 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-700'
                            }`}
                    >
                        {isLoading ? 'Verifying...' : 'Verify Content'}
                    </button>
                </div>
            </div>

            {result && (
                <div className="space-y-6">
                    <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
                        <h2 className="text-xl font-bold text-blue-800 mb-2">Summary</h2>
                        <p className="text-blue-900 leading-relaxed">{result.summary}</p>
                    </div>

                    <h2 className="text-2xl font-semibold text-gray-800 mb-4">Verification Results</h2>
                    <div className="grid gap-4">
                        {result.verified_claims.map((claim, index) => (
                            <div key={index} className={`p-4 rounded-lg border ${getStatusColor(claim.status)}`}>
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className="font-semibold text-lg">{claim.claim_text}</h3>
                                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-white bg-opacity-50">
                                        {claim.status} ({Math.round(claim.confidence * 100)}%)
                                    </span>
                                </div>
                                <p className="text-sm mb-3 opacity-90">{claim.explanation}</p>

                                {claim.evidence_chunks && claim.evidence_chunks.length > 0 && (
                                    <div className="mt-3 pt-3 border-t border-black border-opacity-10">
                                        <p className="text-xs font-bold mb-1 uppercase opacity-70">Supporting Evidence:</p>
                                        <ul className="list-disc list-inside text-xs space-y-1">
                                            {claim.evidence_chunks.slice(0, 2).map((chunk: any, i: number) => (
                                                <li key={i} className="truncate">
                                                    {chunk.text?.substring(0, 100)}...
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default ClaimValidationPage;
