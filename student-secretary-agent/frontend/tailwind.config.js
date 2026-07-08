/** Tailwind config + Campus skin — 浅黄/卡其暖色系. */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 浅黄(amber)做强调色,卡其/stone 做中性色
        campus: {
          50: "#fefce8", 100: "#fef9c3", 200: "#fef08a", 300: "#fde047",
          400: "#facc15", 500: "#eab308", 600: "#ca8a04", 700: "#a16207",
          800: "#854d0e", 900: "#713f12",
        },
        ink: {
          50: "#faf9f5", 100: "#f2efe6", 200: "#e5e0d3", 300: "#d4cdba",
          400: "#a89e87", 500: "#8a7f68", 600: "#6b6253", 700: "#524a3e",
          800: "#3d372e", 900: "#2a2620",
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
