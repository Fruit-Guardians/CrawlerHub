import fs from 'node:fs/promises';
import path from 'node:path';
import sanitizeFilename from 'sanitize-filename';

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function ensureDir(dir: string): Promise<void> {
  await fs.mkdir(dir, { recursive: true });
}

export function timestamp(): string {
  return new Date().toISOString();
}

export function articleIdFromUrl(url: string): string {
  const match = url.match(/\/news\/(\d+)/);
  if (!match) {
    throw new Error(`Could not parse article id from URL: ${url}`);
  }
  return match[1];
}

export function slugifyArticle(id: string, title: string): string {
  const base = sanitizeFilename(title)
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 80);
  return base ? `${id}-${base}` : id;
}

export function unique<T>(items: T[]): T[] {
  return [...new Set(items)];
}

export function stripTags(value: string): string {
  return value.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

export function toAbsoluteUrl(baseUrl: string, candidate: string): string {
  try {
    return new URL(candidate, baseUrl).toString();
  } catch {
    return candidate;
  }
}

export function relativePath(fromFile: string, toFile: string): string {
  return path.relative(path.dirname(fromFile), toFile).split(path.sep).join('/');
}

export function formatCount(count: number): string {
  return new Intl.NumberFormat('zh-CN').format(count);
}
