/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fdf8f6',
          500: '#ea580c',
          600: '#c2410c',
          900: '#7c2d12',
        }
      }
    },
  },
  plugins: [],
}
