import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#1a1a1a",
        surface: "#242424",
        border: "#2e2e2e",
        primary: "#f59e0b",
        "amber-dim": "#78450a",
        text: {
          primary: "#f5f5f5",
          secondary: "#9ca3af",
        },
        success: "#22c55e",
        danger: "#ef4444",
        risk: {
          critical: "#ef4444",
          high: "#f59e0b",
          medium: "#eab308",
          low: "#22c55e",
        }
      },
    },
  },
  plugins: [],
};
export default config;
