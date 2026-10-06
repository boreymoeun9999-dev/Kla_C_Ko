import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  publicDir: fileURLToPath(new URL("../assets", import.meta.url)),
  build: {
    copyPublicDir: false,
  },
});
