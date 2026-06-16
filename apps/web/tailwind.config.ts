import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        accent: 'var(--accent)',
        'accent-bg': 'var(--accent-bg)',
        'accent-deep': 'var(--accent-deep)',
        // Brand-named tokens for moments that need explicit surface
        // (e.g., ink cards on cream).  Ball is logo-only by brand rule —
        // exposed here for the Logo component, not for chips/buttons.
        clay: 'var(--accent)',
        ink: 'var(--ink)',
        'ink-soft': 'var(--ink-soft)',
        cream: 'var(--cream)',
        bone: 'var(--bone)',
        stone: 'var(--stone)',
        'stone-soft': 'var(--stone-soft)',
        ball: 'var(--ball)',
        bg: {
          primary: 'var(--color-background-primary)',
          secondary: 'var(--color-background-secondary)',
          tertiary: 'var(--color-background-tertiary)',
        },
        'text-color': {
          primary: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
          tertiary: 'var(--color-text-tertiary)',
        },
        border: {
          hairline: 'var(--color-border-tertiary)',
          subtle: 'var(--color-border-secondary)',
        },
        success: {
          text: 'var(--color-text-success)',
          bg: 'var(--color-background-success)',
        },
        warning: {
          text: 'var(--color-text-warning)',
          bg: 'var(--color-background-warning)',
        },
        danger: {
          text: 'var(--color-text-danger)',
          bg: 'var(--color-background-danger)',
        },
        info: {
          text: 'var(--color-text-info)',
          bg: 'var(--color-background-info)',
        },
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Text"',
          'system-ui',
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'sans-serif',
        ],
        // Coachito display: Fraunces (SOFT=100).  Reach for this in branded
        // moments — h1/h2 hero, greeting headlines, pull quotes — paired
        // with italic for warmth.  Body stays system sans.
        display: ['Fraunces', 'Georgia', '"Times New Roman"', 'serif'],
      },
      fontSize: {
        'large-title': ['26px', { lineHeight: '1.2', letterSpacing: '-0.4px', fontWeight: '500' }],
        h2: ['18px', { lineHeight: '1.3', fontWeight: '500' }],
        h3: ['16px', { lineHeight: '1.4', fontWeight: '500' }],
        body: ['15px', { lineHeight: '1.55' }],
        caption: ['13px', { lineHeight: '1.4' }],
        section: ['12px', { lineHeight: '1.3' }],
        pill: ['11px', { lineHeight: '1', fontWeight: '500' }],
        footnote: ['11px', { lineHeight: '1.4' }],
      },
      borderRadius: {
        sm: '8px',
        md: '10px',
        lg: '12px',
        xl: '16px',
      },
      minHeight: {
        tap: '44px',
      },
      minWidth: {
        tap: '44px',
      },
    },
  },
  plugins: [],
} satisfies Config;
