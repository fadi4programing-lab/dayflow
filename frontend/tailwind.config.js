/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary:        '#7C6AF7',
        'primary-dark': '#5B4ECC',
        surface:        '#1A1928',
        base:           '#12111A',
        sidebar:        '#0F0E18',
        border:         '#252340',
        muted:          '#7A7891',
        soft:           '#E2E0EE',
      },
      fontFamily: {
        sans: ['Outfit', 'sans-serif'],
      },
    },
  },
  plugins: [],
}