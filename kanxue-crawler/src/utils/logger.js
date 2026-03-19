import pino from "pino";
import { config } from "../config.js";
import { ensureDir } from "./fs.js";

ensureDir(config.paths.logDir);

export const logger = pino({
  level: process.env.LOG_LEVEL || "info",
  transport:
    process.env.NODE_ENV === "production"
      ? undefined
      : {
          target: "pino-pretty",
          options: {
            colorize: true,
            translateTime: "SYS:standard"
          }
        }
});
