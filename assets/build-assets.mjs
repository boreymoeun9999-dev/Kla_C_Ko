import { cpSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = dirname(fileURLToPath(import.meta.url));
const output = join(root, "dist");
mkdirSync(output, { recursive: true });

for (const directory of ["backgrounds", "models", "png", "sounds"]) {
  cpSync(join(root, directory), join(output, directory), { recursive: true });
}
