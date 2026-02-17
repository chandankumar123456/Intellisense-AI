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
        /* Liquid physics */
        'liquid-in': 'liquidIn 320ms cubic-bezier(0.22, 1, 0.36, 1)',
        'liquid-out': 'liquidOut 240ms cubic-bezier(0.22, 1, 0.36, 1)',
        'liquid-rise': 'liquidRise 240ms cubic-bezier(0.22, 1, 0.36, 1)',
        'liquid-settle': 'liquidSettle 480ms cubic-bezier(0.22, 1, 0.36, 1)',
        'liquid-morph': 'liquidMorph 420ms cubic-bezier(0.22, 1, 0.36, 1)',

        /* Glass effects */
        'light-sweep': 'lightSweep 1.8s ease-in-out',
        'glass-pulse': 'glassPulse 3s ease-in-out infinite',
        'specular-shift': 'specularShift 2.4s ease-in-out infinite',
        'float': 'liquidFloat 5s cubic-bezier(0.22, 1, 0.36, 1) infinite',

        /* Standard */
        'fade-in': 'fadeIn 180ms ease-out',
        'fade-in-up': 'fadeInUp 240ms cubic-bezier(0.22, 1, 0.36, 1)',
        'scale-in': 'scaleIn 320ms cubic-bezier(0.22, 1, 0.36, 1)',
        'slide-in-right': 'slideInRight 320ms cubic-bezier(0.22, 1, 0.36, 1)',
        'pulse-soft': 'pulseSoft 600ms ease-in-out infinite',
        'message-in': 'liquidRise 240ms cubic-bezier(0.22, 1, 0.36, 1)',

        /* Liquid dots */
        'liquid-dot-1': 'liquidDot 1.4s ease-in-out infinite',
        'liquid-dot-2': 'liquidDot 1.4s ease-in-out 0.2s infinite',
        'liquid-dot-3': 'liquidDot 1.4s ease-in-out 0.4s infinite',
      },
      keyframes: {
        /* --- Liquid Physics --- */
        liquidIn: {
          '0%': { opacity: '0', transform: 'translateX(-20px) scaleX(0.96)', filter: 'blur(4px)' },
          '60%': { opacity: '1', transform: 'translateX(3px) scaleX(1.01)' },
          '100%': { opacity: '1', transform: 'translateX(0) scaleX(1)', filter: 'blur(0)' },
        },
        liquidOut: {
          '0%': { opacity: '1', transform: 'translateX(0) scaleX(1)' },
          '100%': { opacity: '0', transform: 'translateX(-16px) scaleX(0.97)', filter: 'blur(3px)' },
        },
        liquidRise: {
          '0%': { opacity: '0', transform: 'translateY(8px) scaleY(0.97) scaleX(0.99)' },
          '60%': { opacity: '1', transform: 'translateY(-1px) scaleY(1.005)' },
          '100%': { opacity: '1', transform: 'translateY(0) scaleY(1) scaleX(1)' },
        },
        liquidSettle: {
          '0%': { transform: 'scale(1.01) translateY(-2px)' },
          '40%': { transform: 'scale(0.998) translateY(1px)' },
          '70%': { transform: 'scale(1.002) translateY(-0.5px)' },
          '100%': { transform: 'scale(1) translateY(0)' },
        },
        liquidMorph: {
          '0%': { borderRadius: '14px', transform: 'scale(1)' },
          '30%': { borderRadius: '16px 12px', transform: 'scale(0.998, 1.003)' },
          '100%': { borderRadius: '14px', transform: 'scale(1)' },
        },
        liquidFloat: {
          '0%, 100%': { transform: 'translateY(0) rotate(0deg)' },
          '25%': { transform: 'translateY(-4px) rotate(0.5deg)' },
          '75%': { transform: 'translateY(2px) rotate(-0.3deg)' },
        },

        /* --- Glass Effects --- */
        lightSweep: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        glassPulse: {
          '0%, 100%': { boxShadow: '0 0 20px var(--hover-glow)', opacity: '0.8' },
          '50%': { boxShadow: '0 0 30px var(--hover-glow)', opacity: '1' },
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
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '60%': { opacity: '1', transform: 'scale(1.005)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(100%) scaleX(0.97)' },
          '60%': { transform: 'translateX(-1%) scaleX(1.003)' },
          '100%': { opacity: '1', transform: 'translateX(0) scaleX(1)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '0.3', transform: 'scale(0.85)' },
          '50%': { opacity: '1', transform: 'scale(1.1)' },
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
