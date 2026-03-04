/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'slate': {
          850: '#1e2130',
          900: '#151823',
          950: '#0d0f14',
        }
      }
    },
  },
  plugins: [],
}
