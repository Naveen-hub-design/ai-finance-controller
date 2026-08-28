/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0a0e17",
        surface: "#111726",
        "surface-raised": "#182032",
        "surface-hover": "#1e2740",
        border: "#232c42",
        "border-strong": "#2f3a55",
        muted: "#8b95ab",
        "muted-faint": "#5b6578",
        foreground: "#e8ecf4",
        accent: {
          50: "#e7f0ff",
          100: "#cfe0ff",
          200: "#a5c7ff",
          300: "#76a8ff",
          400: "#4d87f5",
          500: "#2f6fe6",
          600: "#1f58c4",
          700: "#1b4699",
          800: "#1a3a78",
          900: "#182c57",
        },
        success: {
          500: "#34d399",
          600: "#10b981",
        },
        warning: {
          500: "#fbbf24",
          600: "#f59e0b",
        },
        danger: {
          400: "#f87171",
          500: "#ef4444",
          600: "#dc2626",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1rem",
      },
      boxShadow: {
        card: "0 1px 0 rgba(255,255,255,0.02) inset, 0 8px 24px -12px rgba(0,0,0,0.6)",
        focus: "0 0 0 3px rgba(47,111,230,0.4)",
      },
      transitionTimingFunction: {
        "ease-out-quad": "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
      },
    },
  },
  plugins: [],
};
