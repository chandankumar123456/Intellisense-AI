/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        /* ── Light theme (default) ── */
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
        hover_glow: 'var(--hover-glow)',
        active_glow: 'var(--active-glow)',

        success: '#10B981',
        warning: '#F59E0B',
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
        'sidebar': '280px',
        'sidebar-collapsed': '64px',
        'header': '56px',
        'panel': '380px',
        'chat-max': '1100px',
      },
      borderRadius: {
        'glass': '14px',
        'glass-sm': '10px',
        'glass-lg': '18px',
        'pill': '999px',
      },
      animation: {
        /* Liquid physics - Smoother & Slower */
        'liquid-in': 'liquidIn 600ms cubic-bezier(0.2, 0.8, 0.2, 1) forwards',
        'liquid-out': 'liquidOut 400ms cubic-bezier(0.2, 0.8, 0.2, 1) forwards',
        'liquid-rise': 'liquidRise 800ms cubic-bezier(0.2, 0.8, 0.2, 1) forwards',
        'liquid-settle': 'liquidSettle 800ms cubic-bezier(0.2, 0.8, 0.2, 1)',
        'liquid-morph': 'liquidMorph 600ms cubic-bezier(0.2, 0.8, 0.2, 1)',

        /* Glass effects */
        'light-sweep': 'lightSweep 2.5s cubic-bezier(0.4, 0, 0.2, 1)',
        'glass-pulse': 'glassPulse 4s ease-in-out infinite',
        'specular-shift': 'specularShift 5s ease-in-out infinite',
        'float': 'liquidFloat 8s ease-in-out infinite',

        /* Standard - More Premium Timing */
        'fade-in': 'fadeIn 400ms ease-out forwards',
        'fade-in-up': 'fadeInUp 600ms cubic-bezier(0.2, 0.8, 0.2, 1) forwards',
        'scale-in': 'scaleIn 500ms cubic-bezier(0.2, 0.8, 0.2, 1) forwards',
        'slide-in-right': 'slideInRight 500ms cubic-bezier(0.2, 0.8, 0.2, 1) forwards',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'message-in': 'messageIn 500ms cubic-bezier(0.2, 0.8, 0.2, 1) forwards',

        /* Liquid dots */
        'liquid-dot-1': 'liquidDot 1.6s ease-in-out infinite',
        'liquid-dot-2': 'liquidDot 1.6s ease-in-out 0.2s infinite',
        'liquid-dot-3': 'liquidDot 1.6s ease-in-out 0.4s infinite',
      },
      keyframes: {
        /* --- Liquid Physics --- */
        liquidIn: {
          '0%': { opacity: '0', transform: 'translateX(-15px) scaleX(0.98)', filter: 'blur(8px)' },
          '100%': { opacity: '1', transform: 'translateX(0) scaleX(1)', filter: 'blur(0)' },
        },
        liquidOut: {
          '0%': { opacity: '1', transform: 'translateX(0) scaleX(1)', filter: 'blur(0)' },
          '100%': { opacity: '0', transform: 'translateX(-10px) scaleX(0.98)', filter: 'blur(5px)' },
        },
        liquidRise: {
          '0%': { opacity: '0', transform: 'translateY(15px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        liquidSettle: {
          '0%': { transform: 'scale(1.02) translateY(-1px)' },
          '50%': { transform: 'scale(0.99) translateY(0.5px)' },
          '100%': { transform: 'scale(1) translateY(0)' },
        },
        liquidMorph: {
          '0%': { borderRadius: '14px' },
          '50%': { borderRadius: '20px 10px' },
          '100%': { borderRadius: '14px' },
        },
        liquidFloat: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },

        /* --- Glass Effects --- */
        lightSweep: {
          '0%': { backgroundPosition: '-150% 0', opacity: '0' },
          '20%': { opacity: '1' },
          '100%': { backgroundPosition: '150% 0', opacity: '0' },
        },
        glassPulse: {
          '0%, 100%': { boxShadow: '0 0 15px var(--hover-glow)', opacity: '0.9' },
          '50%': { boxShadow: '0 0 25px var(--active-glow)', opacity: '1' },
        },
        specularShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },

        /* --- Standard --- */
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(15px)', filter: 'blur(3px)' },
          '100%': { opacity: '1', transform: 'translateY(0)', filter: 'blur(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.94)', filter: 'blur(2px)' },
          '100%': { opacity: '1', transform: 'scale(1)', filter: 'blur(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        messageIn: {
          '0%': { opacity: '0', transform: 'translateY(10px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '0.6', transform: 'scale(0.98)' },
          '50%': { opacity: '1', transform: 'scale(1.02)' },
        },
        liquidDot: {
          '0%, 100%': { transform: 'translateY(0) scale(1)', opacity: '0.4' },
          '50%': { transform: 'translateY(-5px) scale(1.2)', opacity: '1' },
        },
      },
      boxShadow: {
        'glass': '0 8px 32px var(--glass-shadow)',
        'glass-sm': '0 4px 16px var(--glass-shadow)',
        'glass-lg': '0 16px 48px var(--glass-shadow-lg)',
        'glass-inner': 'inset 0 1px 0 var(--glass-edge)',
        'glow': '0 0 24px var(--hover-glow)',
        'glow-active': '0 0 32px var(--active-glow)',
        'focus-ring': '0 0 0 3px var(--focus-ring), 0 0 16px var(--hover-glow)',
      },
      transitionTimingFunction: {
        'liquid': 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
      transitionDuration: {
        'fast': '180ms',
        'normal': '320ms',
        'slow': '480ms',
      },
    },
  },
  plugins: [],
}
