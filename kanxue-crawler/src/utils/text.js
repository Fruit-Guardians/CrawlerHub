export function cleanText(input) {
  return String(input || "")
    .replace(/\u00a0/g, " ")
    .replace(/\r/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function normalizeFilename(input, fallback = "untitled") {
  const sanitized = cleanText(input)
    .replace(/[<>:"/\\|?*\u0000-\u001F]/g, " ")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");

  return sanitized || fallback;
}

export function truncate(input, maxLength = 180) {
  const text = cleanText(input);
  if (text.length <= maxLength) {
    return text;
  }

  return `${text.slice(0, maxLength - 1)}…`;
}

export function normalizeMarkdownWhitespace(input) {
  return String(input || "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
