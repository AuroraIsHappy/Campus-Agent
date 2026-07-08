/** Tailwind config + Campus skin — 暖黄/卡其色系 (Phase 9 更暖更黄). */
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
          50: "#fdf8ec", 100: "#f5efe0", 200: "#ebe3cf", 300: "#d9cfb6",
          400: "#b3a888", 500: "#94896a", 600: "#756b51", 700: "#5b533f",
          800: "#423d30", 900: "#2c2820",
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '"PingFang SC"', '"Microsoft YaHei"', '"Segoe UI"', "system-ui", "sans-serif"],
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
