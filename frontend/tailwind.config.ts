import type { Config } from "tailwindcss";

// Design tokens per the Step 6 design plan: blueprint/schematic aesthetic.
// ink-* is the navy scale, blueprint/annotation are the two accent colors
// (cool = structural/static, warm = AI-generated), paper is foreground text.
const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#0D1220",
          800: "#161C2C",
          700: "#2A3247",
          600: "#3B4560",
        },
        blueprint: {
          DEFAULT: "#5FB8C9",
          dim: "#3D7883",
        },
        annotation: {
          DEFAULT: "#E8A857",
          dim: "#A87A44",
        },
        paper: {
          DEFAULT: "#EDEEF2",
          dim: "#9AA1B4",
        },
        danger: "#E36A6A",
        success: "#6FBF8B",
      },
      fontFamily: {
        display: ["var(--font-space-grotesk)", "sans-serif"],
        sans: ["var(--font-plex-sans)", "sans-serif"],
        mono: ["var(--font-plex-mono)", "monospace"],
      },
      borderRadius: {
        DEFAULT: "8px",
      },
      backgroundImage: {
        "blueprint-grid":
          "linear-gradient(to right, rgba(95,184,201,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(95,184,201,0.06) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "32px 32px",
      },
    },
  },
  plugins: [],
};

export default config;
