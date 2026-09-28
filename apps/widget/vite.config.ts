import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

// Widget ships as a single IIFE so a plain <script> tag works on any host page.
export default defineConfig({
  plugins: [preact()],
  build: {
    lib: {
      entry: "src/index.ts",
      name: "SpaceChameleonWidget",
      formats: ["iife"],
      fileName: () => "w.js",
    },
    // Loader must stay under 15 KB gzipped (PRD non-functional requirement).
    rollupOptions: { output: { inlineDynamicImports: true } },
  },
});
