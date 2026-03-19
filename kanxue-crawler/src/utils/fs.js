import fs from "node:fs";
import path from "node:path";

export function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

export function writeUtf8(filePath, content) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, content, "utf8");
}

export function writeJson(filePath, payload) {
  writeUtf8(filePath, `${JSON.stringify(payload, null, 2)}\n`);
}

export function writeBuffer(filePath, payload) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, payload);
}
