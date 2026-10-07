import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: { panel: "0 12px 36px rgba(15, 23, 42, .08)" },
      colors: { ink: "#172038", navy: "#10182f", mint: "#13c7a5" },
    },
  },
  plugins: [],
};

export default config;
