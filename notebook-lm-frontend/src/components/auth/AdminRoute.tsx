import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { AuthService } from '../../services/authService';

interface AdminRouteProps {
    children: React.ReactNode;
}

/**
 * Route guard that only allows admin-role users.
 * Non-admins see a 403 page; unauthenticated users redirect to login.
 */
const AdminRoute: React.FC<AdminRouteProps> = ({ children }) => {
    const { isAuthenticated, isLoading, user } = useAuth();
    const location = useLocation();
    const [role, setRole] = useState<string | null>(null);
    const [checking, setChecking] = useState(true);

    useEffect(() => {
        const checkRole = async () => {
            if (!isAuthenticated || isLoading) {
                setChecking(false);
                return;
            }
            try {
                const me = await AuthService.verifyToken();
                setRole((me as any).role || 'user');
            } catch {
                setRole('user');
            } finally {
                setChecking(false);
            }
        };
        checkRole();
    }, [isAuthenticated, isLoading]);

    if (isLoading || checking) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <div className="text-center">
                    <svg
                        className="animate-spin h-12 w-12 text-primary mx-auto"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                    >
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                    </svg>
                    <p className="mt-4 text-text_secondary">Verifying access…</p>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (role !== 'admin') {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background p-8">
                <div className="liquid-glass rounded-glass p-8 max-w-md text-center">
                    <div className="z-content relative">
                        <div className="text-6xl mb-4">🔒</div>
                        <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
                        <p className="text-text_secondary mb-6">
                            You don't have admin privileges to view this page.
                            Contact your administrator for access.
                        </p>
                        <button
                            onClick={() => window.history.back()}
                            className="px-6 py-2.5 rounded-glass-sm bg-primary/20 text-primary hover:bg-primary/30 transition-colors"
                        >
                            Go Back
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return <>{children}</>;
};

export default AdminRoute;
