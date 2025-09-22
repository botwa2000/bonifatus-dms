// tailwind.config.ts
import type { Config } from 'tailwindcss'
import { designTokens } from './src/design/themes/tokens'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Admin colors from design tokens
        'admin-primary': designTokens.colors.admin.primary,
        'admin-secondary': designTokens.colors.admin.secondary,
        'admin-success': designTokens.colors.admin.success,
        'admin-warning': designTokens.colors.admin.warning,
        'admin-danger': designTokens.colors.admin.danger,
        'admin-muted': designTokens.colors.admin.muted,
        
        // User colors for future use
        'user-primary': designTokens.colors.user.primary,
        'user-secondary': designTokens.colors.user.secondary,
        
        // Neutral colors
        neutral: designTokens.colors.neutral,
      },
      fontFamily: {
        sans: designTokens.typography.fontFamily.sans,
        mono: designTokens.typography.fontFamily.mono,
      },
      fontSize: designTokens.typography.fontSize,
      spacing: designTokens.spacing,
      borderRadius: designTokens.borderRadius,
      boxShadow: designTokens.shadows,
    },
  },
  plugins: [],
}
export default config