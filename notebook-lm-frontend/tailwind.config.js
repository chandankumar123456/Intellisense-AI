/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        /* ── Semantic tokens ── */
        background: 'var(--bg-primary)',
        background_secondary: 'var(--bg-secondary)',
        surface: 'var(--glass-surface)',
        surface_elevated: 'var(--glass-elevated)',

        border: 'var(--glass-edge)',
        border_subtle: 'var(--border-subtle)',
        border_focus: 'var(--accent-primary)',

        primary: 'var(--accent-primary)',
        primary_dark: 'var(--accent-primary-dark)',
        primary_light: 'var(--accent-primary-light)',

        secondary: 'var(--accent-secondary)',
        secondary_dark: 'var(--accent-secondary-dark)',

        highlight: 'var(--soft-highlight)',

        success: '#22C55E',
        warning: '#EAB308',
        error: '#EF4444',

        text_primary: 'var(--text-primary)',
        text_secondary: 'var(--text-secondary)',
        text_muted: 'var(--text-muted)',
        text_inverse: 'var(--text-inverse)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
      spacing: {
        'sidebar': '264px',
        'sidebar-collapsed': '0px',
        'header': '52px',
        'panel': '360px',
        'chat-max': '1100px',
      },
      borderRadius: {
        'glass': '10px',
        'glass-sm': '7px',
        'glass-lg': '14px',
        'pill': '999px',
      },
      animation: {
        /* Entry animations */
        'liquid-in': 'liquidIn 280ms cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'liquid-out': 'liquidOut 200ms cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'liquid-rise': 'liquidRise 320ms cubic-bezier(0.22, 1, 0.36, 1) forwards',

        /* Standard */
        'fade-in': 'fadeIn 240ms ease-out forwards',
        'fade-in-up': 'fadeInUp 320ms cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'scale-in': 'scaleIn 280ms cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'slide-in-right': 'slideInRight 280ms cubic-bezier(0.22, 1, 0.36, 1) forwards',
        'message-in': 'messageIn 240ms cubic-bezier(0.22, 1, 0.36, 1) forwards',

        /* Loading dots */
        'liquid-dot-1': 'dotPulse 1.4s ease-in-out infinite',
        'liquid-dot-2': 'dotPulse 1.4s ease-in-out 0.2s infinite',
        'liquid-dot-3': 'dotPulse 1.4s ease-in-out 0.4s infinite',
      },
      keyframes: {
        liquidIn: {
          '0%': { opacity: '0', transform: 'translateX(-12px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        liquidOut: {
          '0%': { opacity: '1', transform: 'translateX(0)' },
          '100%': { opacity: '0', transform: 'translateX(-8px)' },
        },
        liquidRise: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        messageIn: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        dotPulse: {
          '0%, 100%': { transform: 'translateY(0) scale(1)', opacity: '0.4' },
          '50%': { transform: 'translateY(-4px) scale(1.15)', opacity: '1' },
        },
      },
      boxShadow: {
        'glass': '0 2px 8px var(--glass-shadow)',
        'glass-sm': '0 1px 3px var(--glass-shadow)',
        'glass-lg': '0 8px 24px var(--glass-shadow-lg)',
        'focus-ring': '0 0 0 2px var(--focus-ring)',
      },
      transitionTimingFunction: {
        'precision': 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
      transitionDuration: {
        'fast': '160ms',
        'normal': '240ms',
        'slow': '360ms',
      },
    },
  },
  plugins: [],
}
