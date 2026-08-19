import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./lib/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0D0D12",
          surface: "#17171C",
          raised: "#212128",
          border: "#2E2E38",
        },
        accent: {
          DEFAULT: "#7359FA",
          soft: "#241B3D",
          hover: "#8B74FF",
        },
        mist: {
          DEFAULT: "#F5F5F7",
          muted: "#9494A1",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 40px rgba(115, 89, 250, 0.15)",
      },
    },
  },
  plugins: [],
};

export default config;
