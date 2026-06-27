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
        background: "#f8fafc",
        primary: {
          DEFAULT: "#0d9488", // Teal-600
          hover: "#0f766e", // Teal-700
          glow: "rgba(13, 148, 136, 0.15)",
        },
        accent: {
          purple: "#f59e0b", // Replaced purple with amber
          cyan: "#0ea5e9", // Sky-500
        },
        text: {
          primary: "#111827",
          secondary: "#4b5563",
          muted: "#6b7280",
        },
        success: {
          DEFAULT: "#10b981",
          glow: "rgba(16, 185, 129, 0.2)",
        },
        danger: {
          DEFAULT: "#ef4444",
          glow: "rgba(239, 68, 68, 0.2)",
        },
        warning: {
          DEFAULT: "#f59e0b",
          glow: "rgba(245, 158, 11, 0.2)",
        },
        risk: {
          critical: "#ef4444",
          high: "#f97316",
          medium: "#f59e0b",
          low: "#10b981",
        }
      },
      boxShadow: {
        glow: "0 0 20px rgba(99, 102, 241, 0.15)",
        "glow-success": "0 0 20px rgba(16, 185, 129, 0.15)",
        "glow-danger": "0 0 20px rgba(239, 68, 68, 0.15)",
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.05)",
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
