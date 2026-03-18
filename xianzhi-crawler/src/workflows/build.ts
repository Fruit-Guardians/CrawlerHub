import { loadAllArticles } from '../lib/article-store.js';
import { buildStaticSite, runPagefind } from '../lib/site.js';
import { rebuildSqliteIndex } from '../lib/sqlite.js';

export async function buildArtifacts(): Promise<{
  articleCount: number;
  sqlitePath: string;
}> {
  const articles = await loadAllArticles();
  await buildStaticSite(articles);
  const sqlitePath = rebuildSqliteIndex(articles);
  await runPagefind();
  return {
    articleCount: articles.length,
    sqlitePath,
  };
}
