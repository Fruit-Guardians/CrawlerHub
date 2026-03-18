import fs from 'node:fs/promises';
import path from 'node:path';
import { PATHS } from '../config.js';
import { ensureDir } from './utils.js';

export async function ensureProjectDirs(): Promise<void> {
  await Promise.all([
    ensureDir(PATHS.storage),
    ensureDir(PATHS.crawleeStorage),
    ensureDir(PATHS.articles),
    ensureDir(PATHS.feeds),
    ensureDir(PATHS.reports),
    ensureDir(PATHS.sqlite),
    ensureDir(PATHS.dist),
    ensureDir(PATHS.site),
  ]);
}

export async function writeJson(filePath: string, data: unknown): Promise<void> {
  await ensureDir(path.dirname(filePath));
  await fs.writeFile(filePath, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

export async function readJson<T>(filePath: string): Promise<T | null> {
  try {
    const raw = await fs.readFile(filePath, 'utf8');
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export async function exists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

export async function listDirs(root: string): Promise<string[]> {
  try {
    const entries = await fs.readdir(root, { withFileTypes: true });
    return entries.filter((entry) => entry.isDirectory()).map((entry) => path.join(root, entry.name));
  } catch {
    return [];
  }
}
