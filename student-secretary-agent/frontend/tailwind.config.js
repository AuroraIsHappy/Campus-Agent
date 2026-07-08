/** Tailwind config + Campus skin (Phase 8 — warm cozy palette). */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Warm cozy palette: soft rose/coral accent on warm stone neutrals
        campus: {
          50: "#fdf2f4", 100: "#fce7eb", 200: "#f9d0d8", 300: "#f0a8b8",
          400: "#e87a92", 500: "#d9526f", 600: "#c43c5c", 700: "#a32d49",
          800: "#88273e", 900: "#6f2235",
        },
        ink: {
          50: "#faf8f5", 100: "#f3eee7", 200: "#e7ddd0", 700: "#5c5048",
          900: "#3d3530",
        },
      },
      fontFamily: {
        sans: ['"Nunito"', '"PingFang SC"', '"Microsoft YaHei"', '"Segoe UI"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
      },
    },
  },
  plugins: [],
};
