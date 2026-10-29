import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0b0f",
        card: "#13151c",
        line: "#232634",
        text: "#e8eaf0",
        muted: "#8b90a3",
        accent: "#ff6b35",
        good: "#4ade80",
        warn: "#f59e0b",
        bad: "#ef4444",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "ui-sans-serif", "system-ui"],
      },
    },
  },
  plugins: [],
} satisfies Config;
