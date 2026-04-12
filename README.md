# jhell-hugo

Personal academic site for **Jack Hellerstedt**, built with [Hugo](https://gohugo.io/) and the [PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme. It replaces the former WordPress site at [jhell.imipolex.biz](https://jhell.imipolex.biz).

## Requirements

- [Hugo](https://gohugo.io/installation/) **extended** is recommended; minimum version per PaperMod is **0.146.0**.
- Git (for cloning and submodules).

## GitHub repository

Published as **[jhellerstedt/jhell-hugo](https://github.com/jhellerstedt/jhell-hugo)**. A local checkout can live in any folder (for example `jhell-website`).

If the remote does not exist yet, create it and push:

```bash
gh auth login
gh repo create jhellerstedt/jhell-hugo --public --source=. --remote=origin --push
```

Or add `origin` manually and push:

```bash
git remote add origin https://github.com/jhellerstedt/jhell-hugo.git
git push -u origin master
```

## Clone

```bash
git clone --recurse-submodules https://github.com/jhellerstedt/jhell-hugo.git
cd jhell-hugo
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

## Local development

```bash
hugo server -D
```

Then open the local URL Hugo prints (usually `http://localhost:1313/`).

## Production build

```bash
hugo --minify
```

Static output is written to `public/`. Minification is also enabled in `config.yml` via `minify.minifyOutput`.

## Deployment (rsync + nginx)

After a build, sync `public/` to the directory nginx serves (adjust user, host, and path):

```bash
python3 scripts/build_papers_data.py
hugo --minify
rsync -avz --delete public/ user@server:/var/www/jhell.imipolex.biz/html/
```

Use SSH keys, a deploy user with write access only to that tree, and reload or let nginx pick up new files. Configure TLS at the reverse proxy as usual.

## Curated paper RSS → `/feeds/`

Optional RSS 2.0 exports (for example from an **llm-rss** workflow) can be dropped into **`static/rss/*.xml`**. They are copied to **`/rss/<filename>.xml`** on the built site.

The **Feeds** page (`/feeds/`) uses the `llm-rss` shortcode, which reads structured data from **`data/papers.json`**. That file is generated before `hugo` by a small Python script that parses each item’s `<description>` (scores, optional bibliographic lines, abstract).

### Configure the feed source

In **`config.yml`**, under `params.papersFeed`:

- **`url`** — If non-empty, the build script fetches this RSS URL once and writes a single feed entry (no `/rss/…` link row; article links still work).
- **`localDir`** — If `url` is empty, the script reads every `*.xml` in this directory (default `static/rss`).

Environment overrides (useful in CI): **`PAPERS_FEED_URL`**, **`PAPERS_FEED_DIR`**.

### Build commands

```bash
# Normal: merge all static/rss/*.xml (or fetch url if set), then Hugo
python3 scripts/build_papers_data.py
hugo --minify
```

```bash
# Quick check with bundled fixtures (full metadata + legacy + combined affiliation)
python3 scripts/build_papers_data.py --fixtures
hugo --minify
```

The repo ships **`data/papers.json`** with an empty `feeds` array so `hugo` runs without running the script first; the Feeds page then shows a short “no data” note until you regenerate.

## Theme

PaperMod lives in `themes/PaperMod` as a **git submodule**. Update it with:

```bash
cd themes/PaperMod && git pull origin master && cd ../.. && git add themes/PaperMod && git commit -m "chore: bump PaperMod"
```

## License

Site content © Jack Hellerstedt unless otherwise noted. The PaperMod theme has its own [license](https://github.com/adityatelange/hugo-PaperMod/blob/master/LICENSE).
