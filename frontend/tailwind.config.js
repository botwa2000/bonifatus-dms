// frontend/tailwind.config.js

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        admin: {
          primary: '#1e40af',
          secondary: '#6366f1',
          success: '#059669',
          warning: '#d97706',
          danger: '#dc2626',
        },
        semantic: {
          // State backgrounds (light mode)
          'success-bg': '#f0fdf4',      // green-50
          'warning-bg': '#fffbeb',      // yellow-50
          'error-bg': '#fef2f2',        // red-50
          'info-bg': '#eff6ff',         // blue-50

          // State backgrounds (stronger - for badges)
          'success-bg-strong': '#dcfce7',  // green-100
          'warning-bg-strong': '#fef3c7',  // yellow-100
          'error-bg-strong': '#fee2e2',    // red-100
          'info-bg-strong': '#dbeafe',     // blue-100

          // State text colors
          'success-text': '#065f46',    // green-800
          'warning-text': '#92400e',    // yellow-800
          'error-text': '#991b1b',      // red-800
          'info-text': '#1e3a8a',       // blue-800

          // State borders
          'success-border': '#bbf7d0',  // green-200
          'warning-border': '#fde68a',  // yellow-200
          'error-border': '#fecaca',    // red-200
          'info-border': '#bfdbfe',     // blue-200
        },
        feature: {
          // Feature card accent colors
          automation: '#3b82f6',      // blue-500
          search: '#10b981',          // green-500
          cloud: '#8b5cf6',           // purple-500
          upload: '#f97316',          // orange-500
          email: '#ef4444',           // red-500
          language: '#14b8a6',        // teal-500
        },
        neutral: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d4d4d4',
          400: '#a3a3a3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        },
      },
      fontFamily: {
        sans: ['var(--font-geist-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-geist-mono)', 'monospace'],
      },
    },
  },
  plugins: [],
};