import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
    theme: Theme;
    toggleTheme: () => void;
    isTransitioning: boolean;
}

const ThemeContext = createContext<ThemeContextType>({
    theme: 'light',
    toggleTheme: () => { },
    isTransitioning: false,
});

export const useTheme = () => useContext(ThemeContext);

interface ThemeProviderProps {
    children: ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
    const [theme, setTheme] = useState<Theme>(() => {
        const saved = localStorage.getItem('intellisense-theme');
        if (saved === 'dark' || saved === 'light') return saved;
        return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    });
    const [isTransitioning, setIsTransitioning] = useState(false);

    useEffect(() => {
        const root = document.documentElement;
        root.setAttribute('data-theme', theme);
        root.classList.remove('light', 'dark');
        root.classList.add(theme);
        localStorage.setItem('intellisense-theme', theme);
    }, [theme]);

    const toggleTheme = useCallback(() => {
        setIsTransitioning(true);
        document.documentElement.classList.add('theme-transitioning');

        // Start morphing
        requestAnimationFrame(() => {
            setTheme(prev => prev === 'light' ? 'dark' : 'light');

            // Remove transition class after morph completes
            setTimeout(() => {
                setIsTransitioning(false);
                document.documentElement.classList.remove('theme-transitioning');
            }, 420);
        });
    }, []);

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme, isTransitioning }}>
            {children}
        </ThemeContext.Provider>
    );
};

export default ThemeContext;
