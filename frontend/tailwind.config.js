/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0a0f",
        surface: "#161b22",
        "primary-gradient": "linear-gradient(to right, #6366f1, #8b5cf6, #a855f7)",
        accent: "#6366f1",
        glow: "#06b6d4",
        muted: "#94a3b8",
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        "glow-pulse": "glow-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-up": "fade-up 0.5s ease-out forwards",
        "gradient-shift": "gradient-shift 3s ease infinite",
        marquee: "marquee 28s linear infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-20px)" },
        },
        "glow-pulse": {
          "0%, 100%": { opacity: 1, boxShadow: "0 0 20px rgba(99, 102, 241, 0.4)" },
          "50%": { opacity: 0.7, boxShadow: "0 0 40px rgba(6, 182, 212, 0.6)" },
        },
        "fade-up": {
          "0%": { transform: "translateY(20px)", opacity: 0 },
          "100%": { transform: "translateY(0)", opacity: 1 },
        },
        "gradient-shift": {
          "0%, 100%": { "background-position": "0% 50%" },
          "50%": { "background-position": "100% 50%" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
      backgroundImage: {
        'dots': 'radial-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px)',
      }
    },
  },
  plugins: [],
}
