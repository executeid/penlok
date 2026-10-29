/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    fontFamily: {
      sans: ['Inter', 'sans-serif'],
      mono: ['"JetBrains Mono"', 'monospace'],
    },
    extend: {
      colors: {
        background: '#121212',
        surface: '#1E1E1E',
        surfaceHover: '#252525',
        border: '#2C2C2E',
        cyan: {
          accent: '#00E5FF',
          DEFAULT: '#00E5FF',
        },
        alert: {
          red: '#FF453A',
          bg: '#3A1C1C',
        },
        lime: {
          green: '#32D74B',
          DEFAULT: '#32D74B',
        },
        text: {
          primary: '#FFFFFF',
          secondary: '#98989D',
        },
      },
      borderRadius: {
        card: '16px',
        btn: '8px',
        pill: '9999px',
      },
      spacing: {
        '2': '8px',
        '4': '16px',
        '5': '20px',
        '6': '24px',
        '8': '32px',
      },
    },
  },
  plugins: [],
}
