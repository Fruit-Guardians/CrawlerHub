import crypto from "node:crypto";

export function sha1(input) {
  return crypto.createHash("sha1").update(input).digest("hex");
}

export function sha256(input) {
  return crypto.createHash("sha256").update(input).digest("hex");
}
