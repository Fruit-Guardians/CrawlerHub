import { CrawlDatabase } from "./store/db.js";
import { KanxueCrawleeService } from "./crawlee/kanxue-crawlee.js";
import { MarkdownExporter } from "./export/markdown-exporter.js";
import { RawRefreshService } from "./export/raw-refresh.js";
import { logger } from "./utils/logger.js";
import { waitForEnter } from "./utils/terminal.js";
import { BrowserManager } from "./browser/browser-manager.js";

function parseArgs(argv) {
  const [command = "run", ...rest] = argv.slice(2);
  const options = {};

  for (let index = 0; index < rest.length; index += 1) {
    const token = rest[index];
    if (!token.startsWith("--")) {
      continue;
    }

    const key = token.slice(2);
    const next = rest[index + 1];
    if (next && !next.startsWith("--")) {
      options[key] = next;
      index += 1;
    } else {
      options[key] = true;
    }
  }

  return { command, options };
}

function printStats(stats) {
  console.log("\n任务统计:");
  for (const row of stats.tasks) {
    console.log(`- ${row.type}/${row.status}: ${row.count}`);
  }

  console.log("\n文章统计:");
  for (const row of stats.articles) {
    console.log(`- ${row.channel}: ${row.count}`);
  }

  console.log(`\n总文章数: ${stats.articleTotal}`);
  console.log(`数据库: ${stats.dbFile}`);
}

function printSearchResults(rows) {
  if (!rows.length) {
    console.log("没有命中结果。");
    return;
  }

  rows.forEach((row, index) => {
    console.log(`${index + 1}. ${row.title || "Untitled"}`);
    console.log(`   作者: ${row.author || "未知"} | 分类: ${row.category || "未分类"} | 发布时间: ${row.published_at || "未知"}`);
    console.log(`   链接: ${row.url || ""}`);
    console.log(`   Markdown: ${row.markdown_path || ""}`);
    console.log(`   摘要: ${row.snippet || ""}`);
  });
}

async function main() {
  const { command, options } = parseArgs(process.argv);
  const db = new CrawlDatabase();
  const crawler = new KanxueCrawleeService({ db });
  const browserManager = new BrowserManager();

  try {
    if (command === "bootstrap-session") {
      const session = await browserManager.bootstrapSession();
      console.log("浏览器已打开。请在页面中完成看雪验证或登录，完成后回到终端按回车保存会话。");
      await waitForEnter("");
      await session.save();
      await session.page.close().catch(() => {});
      await session.context.close().catch(() => {});
      console.log("会话已保存到 data/session/kanxue-storage-state.json");
      return;
    }

    if (command === "discover") {
      console.log(JSON.stringify(await crawler.discover(), null, 2));
      return;
    }

    if (command === "crawl") {
      console.log(JSON.stringify(await crawler.crawl(), null, 2));
      return;
    }

    if (command === "export-markdown") {
      const exporter = new MarkdownExporter({ db });
      console.log(JSON.stringify(await exporter.run(), null, 2));
      return;
    }

    if (command === "refresh-raw") {
      const refresher = new RawRefreshService({ db });
      console.log(JSON.stringify(refresher.run(), null, 2));
      return;
    }

    if (command === "search") {
      const query = options.q || options.query;
      if (!query) {
        throw new Error("search 命令需要通过 --q 提供查询词");
      }

      printSearchResults(db.searchArticles(query, Number(options.limit || 10)));
      return;
    }

    if (command === "stats") {
      printStats(db.getStats());
      return;
    }

    const discoverResult = await crawler.discover();
    const crawlResult = await crawler.crawl();
    const exporter = new MarkdownExporter({ db });
    const exportResult = await exporter.run();

    console.log(
      JSON.stringify(
        {
          discover: discoverResult,
          crawl: crawlResult,
          export: exportResult
        },
        null,
        2
      )
    );
  } catch (error) {
    logger.error({ error: error.message, stack: error.stack }, "运行失败");
    process.exitCode = 1;
  } finally {
    await browserManager.close();
  }
}

main();
