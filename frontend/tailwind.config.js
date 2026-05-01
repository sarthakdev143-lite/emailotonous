/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        shell: "#f4efe8",
        canvas: "#fbf8f3",
        panel: "#fffdf9",
        stroke: "#d8cfc0",
        ink: "#1e2a28",
        mist: "#677775",
        brand: "#1f7066",
        brandSoft: "#d9efe9",
        gold: "#b98836",
        rose: "#f3d6d0",
      },
      fontFamily: {
        sans: ["Manrope", "system-ui", "sans-serif"],
        serif: ["Fraunces", "Georgia", "serif"],
      },
      boxShadow: {
        panel: "0 22px 45px -24px rgba(31, 53, 49, 0.28)",
      },
      backgroundImage: {
        "shell-gradient":
          "radial-gradient(circle at top left, rgba(217, 239, 233, 0.9), transparent 36%), radial-gradient(circle at top right, rgba(243, 214, 208, 0.7), transparent 28%)",
      },
    },
  },
  plugins: [],
};
