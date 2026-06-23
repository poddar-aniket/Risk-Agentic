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
        background: "#080b11",
        surface: {
          DEFAULT: "rgba(17, 24, 39, 0.7)",
          card: "rgba(22, 30, 49, 0.6)",
          hover: "rgba(31, 41, 55, 0.8)",
        },
        border: {
          DEFAULT: "rgba(255, 255, 255, 0.08)",
          glow: "rgba(99, 102, 241, 0.2)",
        },
        primary: {
          DEFAULT: "#6366f1", // Indigo
          hover: "#4f46e5",
          glow: "rgba(99, 102, 241, 0.15)",
        },
        accent: {
          purple: "#a855f7",
          cyan: "#06b6d4",
        },
        text: {
          primary: "#f3f4f6",
          secondary: "#9ca3af",
          muted: "#6b7280",
        },
        success: {
          DEFAULT: "#10b981",
          glow: "rgba(16, 185, 129, 0.2)",
        },
        danger: {
          DEFAULT: "#f43f5e",
          glow: "rgba(244, 63, 94, 0.2)",
        },
        warning: {
          DEFAULT: "#fbbf24",
          glow: "rgba(251, 191, 36, 0.2)",
        },
        risk: {
          critical: "#f43f5e",
          high: "#f97316",
          medium: "#eab308",
          low: "#10b981",
        }
      },
      boxShadow: {
        glow: "0 0 20px rgba(99, 102, 241, 0.15)",
        "glow-success": "0 0 20px rgba(16, 185, 129, 0.15)",
        "glow-danger": "0 0 20px rgba(244, 63, 94, 0.15)",
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
      },
      animation: {
        "pulse-glow": "pulseGlow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "spin-slow": "spin 8s linear infinite",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: ".8", transform: "scale(1.02)" },
        }
      }
    },
  },
  plugins: [],
};
export default config;

