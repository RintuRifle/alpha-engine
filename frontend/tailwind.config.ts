import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#07090c",
        panel: "#0b0f14",
        panel2: "#0e141b",
        panel3: "#121a24",
        line: "#182230",
        line2: "#22304200",
        text: "#d7e0ea",
        muted: "#5b6b7d",
        dim: "#3b4a5c",
        amber: "#f7a600",
        up: "#0ecb81",
        down: "#f6465d",
        cyan: "#22d3ee",
        violet: "#a78bfa",
      },
      fontFamily: {
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        sans: ["var(--font-sans)", "ui-sans-serif", "sans-serif"],
      },
      fontSize: {
        micro: ["10px", "14px"],
        xxs: ["11px", "15px"],
      },
      keyframes: {
        led: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition: "400px 0" },
        },
        blink: {
          "0%, 49%": { opacity: "1" },
          "50%, 100%": { opacity: "0" },
        },
      },
      animation: {
        led: "led 1.6s ease-in-out infinite",
        shimmer: "shimmer 1.4s linear infinite",
        blink: "blink 1.1s step-start infinite",
      },
    },
  },
  plugins: [],
};
export default config;
