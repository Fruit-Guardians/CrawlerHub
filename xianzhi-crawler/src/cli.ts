import { ensureProjectDirs } from './lib/fs.js';
import { loadAllArticles } from './lib/article-store.js';
import { PATHS, CONFIG } from './config.js';
import { backfillUntilDate } from './workflows/backfill.js';
import { buildArtifacts } from './workflows/build.js';
import { crawlArticleDetails } from './workflows/crawl.js';
import { seedWorkflows } from './workflows/seed.js';

async function main(): Promise<void> {
  await ensureProjectDirs();

  const command = process.argv[2] ?? 'all';

  if (command === 'seed') {
    const result = await seedWorkflows();
    console.log(
      JSON.stringify(
        {
          command,
          feedEntries: result.feedEntries.length,
          historyUrls: result.historyUrls.length,
          queue: 'storage/crawlee/request_queues/xianzhi-article-details',
        },
        null,
        2,
      ),
    );
    return;
  }

  if (command === 'crawl') {
    await crawlArticleDetails();
    const articles = await loadAllArticles();
    console.log(
      JSON.stringify(
        {
          command,
          articles: articles.length,
          articlesDir: PATHS.articles,
        },
        null,
        2,
      ),
    );
    return;
  }

  if (command === 'site' || command === 'index') {
    const result = await buildArtifacts();
    console.log(
      JSON.stringify(
        {
          command,
          articles: result.articleCount,
          sqlitePath: result.sqlitePath,
          siteDir: PATHS.site,
        },
        null,
        2,
      ),
    );
    return;
  }

  if (command === 'all') {
    const seeded = await seedWorkflows(CONFIG.defaultListPages);
    await crawlArticleDetails();
    const built = await buildArtifacts();
    console.log(
      JSON.stringify(
        {
          command,
          feedEntries: seeded.feedEntries.length,
          historyUrls: seeded.historyUrls.length,
          articles: built.articleCount,
          sqlitePath: built.sqlitePath,
          siteDir: PATHS.site,
        },
        null,
        2,
      ),
    );
    return;
  }

  if (command === 'backfill') {
    const untilDate = process.argv[3] ?? process.env.XZ_UNTIL_DATE;
    if (!untilDate) {
      throw new Error('Missing cutoff date. Use: npm run backfill -- 2025-04-23');
    }

    const result = await backfillUntilDate(untilDate);
    console.log(
      JSON.stringify(
        {
          command,
          untilDate: result.untilDate,
          untilDateUtc: result.untilDateUtc,
          queueName: result.queueName,
          seededPages: result.seededPages,
          queuedUrls: result.queuedUrls,
          skippedExisting: result.skippedExisting,
          articles: result.articleCount,
          sqlitePath: result.sqlitePath,
          siteDir: PATHS.site,
        },
        null,
        2,
      ),
    );
    return;
  }

  throw new Error(`Unknown command: ${command}`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack ?? error.message : String(error));
  process.exitCode = 1;
});
