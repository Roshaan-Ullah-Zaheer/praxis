import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Theme-aware tokens. Channel triplets live in globals.css (:root = dark,
        // html.light = light) so the whole UI flips with a single class.
        canvas: "rgb(var(--canvas) / <alpha-value>)",
        surface: {
          DEFAULT: "rgb(var(--surface) / <alpha-value>)",
          raised: "rgb(var(--surface-raised) / <alpha-value>)",
          hover: "rgb(var(--surface-hover) / <alpha-value>)",
        },
        ink: {
          DEFAULT: "rgb(var(--ink) / <alpha-value>)",
          muted: "rgb(var(--ink-muted) / <alpha-value>)",
          faint: "rgb(var(--ink-faint) / <alpha-value>)",
        },
        // emerald = grounded / verified / trust
        trust: {
          DEFAULT: "rgb(var(--trust) / <alpha-value>)",
          bright: "rgb(var(--trust-bright) / <alpha-value>)",
          dim: "rgb(var(--trust-dim) / <alpha-value>)",
        },
        // amber/red = contradiction / alert
        conflict: {
          DEFAULT: "rgb(var(--conflict) / <alpha-value>)",
          red: "rgb(var(--conflict-red) / <alpha-value>)",
          dim: "rgb(var(--conflict-dim) / <alpha-value>)",
        },
        info: "rgb(var(--info) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-grotesk)", "var(--font-inter)", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(16,185,129,0.30), 0 10px 40px rgba(16,185,129,0.12)",
        panel: "0 1px 0 rgba(255,255,255,0.03) inset, 0 20px 60px rgba(0,0,0,0.4)",
      },
    },
  },
  plugins: [],
};

export default config;
