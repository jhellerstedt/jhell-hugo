# jhell-hugo

Personal academic site for **Jack Hellerstedt**, built with [Hugo](https://gohugo.io/) and the [PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme. It replaces the former WordPress site at [jhell.imipolex.biz](https://jhell.imipolex.biz).

## Requirements

- [Hugo](https://gohugo.io/installation/) **extended** is recommended; minimum version per PaperMod is **0.146.0**.
- Git (for cloning and submodules).

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
hugo --minify
rsync -avz --delete public/ user@server:/var/www/jhell.imipolex.biz/html/
```

Use SSH keys, a deploy user with write access only to that tree, and reload or let nginx pick up new files. Configure TLS at the reverse proxy as usual.

## LLM / RSS XML feeds in `static/rss/`

Optional XML exports (for example from an **llm-rss** workflow or other tooling) can be dropped into `static/rss/` as `*.xml`. They are published at **`/rss/<filename>.xml`** on the live site.

The **LLM RSS feeds** page (`/feeds/`) uses the `llm-rss` shortcode to list those files and show each file’s first `<title>` when present. Replace `static/rss/example-llm-export.xml` with your real exports when ready.

## Theme

PaperMod lives in `themes/PaperMod` as a **git submodule**. Update it with:

```bash
cd themes/PaperMod && git pull origin master && cd ../.. && git add themes/PaperMod && git commit -m "chore: bump PaperMod"
```

## License

Site content © Jack Hellerstedt unless otherwise noted. The PaperMod theme has its own [license](https://github.com/adityatelange/hugo-PaperMod/blob/master/LICENSE).
