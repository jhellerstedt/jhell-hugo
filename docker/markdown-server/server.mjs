/**
 * Serves HTML from the static site root as Markdown when nginx proxies
 * markdown-preference requests (Accept: text/markdown).
 */
import http from "node:http";
import { existsSync, readFileSync, statSync } from "node:fs";
import { join, normalize, relative, resolve } from "node:path";
import { JSDOM } from "jsdom";
import TurndownService from "turndown";

const HTML_ROOT = process.env.HTML_ROOT || "/usr/share/nginx/html";
const PORT = Number(process.env.MARKDOWN_SERVER_PORT || 3000, 10);
const MAX_BYTES = 2_097_152; // align with Cloudflare Markdown for Agents limit

function wantsMarkdown(accept) {
  if (!accept || typeof accept !== "string") return false;
  return /(^|,|\s)text\/markdown(\s*;|\s*,|\s*$)/i.test(accept);
}

function underRoot(root, candidate) {
  const rel = relative(normalize(root), normalize(candidate));
  return rel !== "" && !rel.startsWith("..") && !normalize(rel).startsWith(`..${normalize("/")}`);
}

function pathnameFromUrl(urlPath) {
  const raw = (urlPath || "/").split("?")[0] || "/";
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

function resolveHtmlFile(urlPath) {
  const pathname = pathnameFromUrl(urlPath);
  const root = resolve(HTML_ROOT);
  const rel = pathname.replace(/^\/+/, "");

  // Literal HTML files (e.g. /index.html, /blog/index.html) — Hugo writes these paths on disk.
  if (rel.endsWith(".html")) {
    const direct = resolve(join(root, rel));
    if (underRoot(root, direct) && existsSync(direct) && statSync(direct).isFile()) {
      return direct;
    }
  }

  const candidates = [];

  if (pathname === "/" || pathname === "") {
    candidates.push(join(root, "index.html"));
  } else {
    const stripped = rel;
    if (pathname.endsWith("/")) {
      candidates.push(join(root, stripped, "index.html"));
    } else {
      candidates.push(join(root, stripped, "index.html"));
      candidates.push(join(root, `${stripped}.html`));
    }
  }

  for (const abs of candidates) {
    const resolved = resolve(abs);
    if (!underRoot(root, resolved)) continue;
    if (existsSync(resolved) && statSync(resolved).isFile()) return resolved;
  }

  if (pathname !== "/" && !pathname.endsWith("/")) {
    const withSlash = join(root, pathname.replace(/^\/+/, ""), "index.html");
    const resolved = resolve(withSlash);
    if (underRoot(root, resolved) && existsSync(resolved) && statSync(resolved).isFile()) {
      return resolved;
    }
  }

  return null;
}

function estimateTokens(text) {
  return String(Math.ceil(Buffer.byteLength(text, "utf8") / 4));
}

function errorBody(req, text) {
  return req.method === "HEAD" ? "" : text;
}

function htmlToMarkdown(html) {
  const dom = new JSDOM(html);
  const { document } = dom.window;
  const title = document.querySelector("title")?.textContent?.trim() || "";
  const turndown = new TurndownService({
    headingStyle: "atx",
    codeBlockStyle: "fenced",
  });
  const body = document.body;
  const core = turndown.turndown(body ? body.innerHTML : document.documentElement.outerHTML);
  if (title) {
    return `---\ntitle: ${title.replace(/\n/g, " ")}\n---\n\n${core}`;
  }
  return core;
}

const server = http.createServer((req, res) => {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { Allow: "GET, HEAD" });
    res.end();
    return;
  }

  if (!wantsMarkdown(req.headers.accept || "")) {
    res.writeHead(406, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(errorBody(req, "Not Acceptable: this service requires Accept: text/markdown\n"));
    return;
  }

  const file = resolveHtmlFile(req.url || "/");
  if (!file) {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(errorBody(req, "Not Found\n"));
    return;
  }

  let st;
  try {
    st = statSync(file);
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(errorBody(req, "Not Found\n"));
    return;
  }

  if (st.size > MAX_BYTES) {
    res.writeHead(413, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(errorBody(req, "Payload Too Large\n"));
    return;
  }

  let html;
  try {
    html = readFileSync(file, "utf8");
  } catch {
    res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(errorBody(req, "Internal Server Error\n"));
    return;
  }

  let markdown;
  try {
    markdown = htmlToMarkdown(html);
  } catch (err) {
    console.error(err);
    res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(errorBody(req, "Conversion failed\n"));
    return;
  }

  const tokens = estimateTokens(markdown);
  const headers = {
    "Content-Type": "text/markdown; charset=utf-8",
    Vary: "Accept",
    "x-markdown-tokens": tokens,
  };
  if (req.method === "HEAD") {
    res.writeHead(200, headers);
    res.end();
    return;
  }
  res.writeHead(200, headers);
  res.end(markdown);
});

server.listen(PORT, "127.0.0.1", () => {
  console.error(`markdown-for-agents listening on 127.0.0.1:${PORT} root=${HTML_ROOT}`);
});
