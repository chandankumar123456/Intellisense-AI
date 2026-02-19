import React, { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

// Contexts
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import { SessionProvider } from './contexts/SessionContext';
import { ChatProvider } from './contexts/ChatContext';

// Components
import ProtectedRoute from './components/auth/ProtectedRoute';
import AdminRoute from './components/auth/AdminRoute';
import ErrorBoundary from './components/common/ErrorBoundary';
import LoadingSpinner from './components/common/LoadingSpinner';

// Lazy load pages for code splitting
const LandingPage = lazy(() => import('./pages/LandingPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const SignupPage = lazy(() => import('./pages/SignupPage'));
const AppLayout = lazy(() => import('./components/layout/AppLayout'));
const HomePage = lazy(() => import('./pages/HomePage'));
const ChatPage = lazy(() => import('./pages/ChatPage'));
const HistoryPage = lazy(() => import('./pages/HistoryPage'));
const WebSourcesPage = lazy(() => import('./pages/WebSourcesPage'));
const YouTubePage = lazy(() => import('./pages/YouTubePage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));
const ClaimValidationPage = lazy(() => import('./pages/ClaimValidationPage'));
const AdminPage = lazy(() => import('./pages/AdminPage'));
const StudentKnowledgePage = lazy(() => import('./pages/StudentKnowledgePage'));

function App() {
  return (
    <ThemeProvider>
      <ErrorBoundary>
        <AuthProvider>
          <SessionProvider>
            <ChatProvider>
              <Router>
                <a
                  href="#main-content"
                  className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-white focus:rounded-lg"
                >
                  Skip to main content
                </a>
                <div className="min-h-screen bg-background" id="main-content">
                  <Suspense
                    fallback={
                      <div className="min-h-screen flex items-center justify-center">
                        <LoadingSpinner size="lg" />
                      </div>
                    }
                  >
                    <Routes>
                      {/* Public routes */}
                      <Route path="/" element={<LandingPage />} />
                      <Route path="/login" element={<LoginPage />} />
                      <Route path="/signup" element={<SignupPage />} />

                      {/* Protected routes */}
                      <Route
                        path="/app"
                        element={
                          <ProtectedRoute>
                            <AppLayout />
                          </ProtectedRoute>
                        }
                      >
                        <Route index element={<Navigate to="/app/chat" replace />} />
                        <Route path="home" element={<HomePage />} />
                        <Route path="chat" element={<ChatPage />} />
                        <Route path="history" element={<HistoryPage />} />
                        <Route path="web" element={<WebSourcesPage />} />
                        <Route path="youtube" element={<YouTubePage />} />
                        <Route path="verification" element={<ClaimValidationPage />} />
                        <Route path="knowledge" element={<StudentKnowledgePage />} />
                        <Route path="admin" element={<AdminRoute><AdminPage /></AdminRoute>} />
                        <Route path="settings" element={<SettingsPage />} />
                      </Route>

                      {/* 404 Not Found */}
                      <Route path="*" element={<NotFoundPage />} />
                    </Routes>
                  </Suspense>
                </div>
                <Toaster
                  position="top-right"
                  toastOptions={{
                    duration: 4000,
                    style: {
                      background: 'var(--toast-bg)',
                      color: 'var(--toast-text)',
                      backdropFilter: 'blur(12px)',
                      borderRadius: '14px',
                      border: '1px solid var(--glass-edge)',
                      boxShadow: '0 8px 32px var(--glass-shadow)',
                    },
                    success: {
                      duration: 3000,
                      iconTheme: {
                        primary: '#10B981',
                        secondary: '#fff',
                      },
                    },
                    error: {
                      duration: 5000,
                      iconTheme: {
                        primary: '#EF4444',
                        secondary: '#fff',
                      },
                    },
                  }}
                />
              </Router>
            </ChatProvider>
          </SessionProvider>
        </AuthProvider>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
