/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#6366f1', // Indigo 500
        primary_dark: '#4f46e5', // Indigo 600
        secondary: '#8b5cf6', // Violet 500
        success: '#10B981',
        warning: '#F59E0B',
        error: '#EF4444',
        background: '#f8fafc', // Slate 50
        surface: '#ffffff',
        border: '#e2e8f0', // Slate 200
        text_primary: '#0f172a', // Slate 900
        text_secondary: '#64748b', // Slate 500
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      spacing: {
        'sidebar': '240px',
        'header': '64px',
        'container-max': '1200px',
        'message-gap': '1rem',
      },
      animation: {
        'fade-in-up': 'fadeInUp 0.3s ease',
        'fade-in': 'fadeIn 0.2s ease',
      },
      keyframes: {
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
