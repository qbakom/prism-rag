import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Front to czysta SPA gadająca z FastAPI (domyślnie http://localhost:8000).
// Tailwind v4 wpinamy jako plugin Vite - bez osobnego configu/PostCSS.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
});
