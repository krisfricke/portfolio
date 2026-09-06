# Articles by Kris Fricke — page-turning reader

A static site: a cover-anchored, scroll-driven reader for magazine articles, with the pages shown as
printed (live, selectable text over the page art) plus plain-text versions of every article for
search engines, screen readers and text-only browsers.

Everything is static files. No server-side code, no build step needed to *serve* it — only to *change* it.

## Publish on GitHub Pages

1. Create a new public repository, e.g. `portfolio` (the name becomes the URL: `https://krisfricke.github.io/portfolio/`).
2. Put the **contents of this folder** at the root of the repository (so `index.html` is at the top level) and push.
3. Repository → Settings → Pages → *Build and deployment*: Source **Deploy from a branch**, branch **main**, folder **/ (root)**. Save.
4. A minute later the site is live at `https://krisfricke.github.io/<repo>/`.

If you name the repository anything other than `portfolio`, change `base` in `_config.json` and run the two build
scripts below (the base URL is baked into share links, citations' links, the sitemap and canonical tags).

Files and folders starting with an underscore (`_build/`, `_config.json`, `_articles_meta.json`) are ignored by
GitHub Pages' default Jekyll processing, so the build tooling stays in the repo without being published.

## Layout

    index.html              the reader
    pages/<id>/N.html       one document per printed page: background JPEG + positioned live text
    pages/<id>/cover.jpg    first page, used as the article's cover card
    pages/<id>/text.json    extracted text (source for the text versions)
    article/<id>/index.html plain-text version of each article, with citation (crawlable, screen-reader friendly)
    article/index.html      text-only list of all articles
    assets/bee/             the cursor bee: body + two wings, cut from the original drawing
    assets/fonts/           Carlito, Liberation Serif, TeX Gyre Pagella (metric stand-ins for Calibri, Times, Palatino)
    sitemap.xml, robots.txt

## Adding an article

1. Drop the PDF next to this folder (the build looks in the parent directory) or, for Australian Bee Journal
   pieces, point at the issue PDF and a page range.
2. Add an entry to `_articles_meta.json`. Fields: `id` (used in URLs — keep it stable), `pub`, `year`, `month`,
   `vol`, `no`, `pages` `[first, last]` as printed, `title`, `tags`, and `src` (a filename, or
   `{"iss": "...", "p": [first, last]}` for a page range within an issue).
3. Run, from this folder:

        python3 _build/buildpages.py <id>     # renders pages/<id>/
        python3 _build/pics.py <id>           # cuts the pictures out at native resolution for the enlarger
        python3 _build/assemble.py            # rebuilds index.html
        python3 _build/static.py              # rebuilds article/, sitemap.xml, robots.txt

   `buildpages.py` needs Python 3 with `pymupdf` (`pip install pymupdf`). The other two need nothing extra.

A new publication needs nothing special: the "By publication" list and the citation format are driven by the
data. If a publication has no volume/issue numbering, leave `vol`/`no` out and the citation omits them.

## Citation format

APA-style as requested: year only, article title in quotes, publication in italics —

> Fricke, K. (2019). "Beekeeping Development Project: Kyrgyzstan." *American Bee Journal*, 159(6), 701–706.

The Cite button copies rich text (italics preserved) where the browser allows it, plain text otherwise.

## Links that fix the order

Add `#/newest` or `#/oldest` to the address to open the list in that order (the visitor's own saved preference is
left alone). It also works as a prefix on any other link:

    https://krisfricke.github.io/portfolio/#/oldest
    https://krisfricke.github.io/portfolio/#/oldest/topic/varroa
    https://krisfricke.github.io/portfolio/#/newest/read/abj-2019-06

## Reader controls

- The list is a stack of covers, each sitting on its remaining pages. Click one and the pages shoot down and unfold in place;
  click the sky around an open article (or the **Next article** arrow after its last page; on a phone, a brisk flick up from the end)
  to restack it. The **Newest / Oldest on top** button flips the stack: at the top of the list you stay at the top; anywhere else you stay on
  the article you were looking at. **Back to top** closes anything open and returns to the head of the list.
- **By publication** and **By topic** open a lane to the right; the left-edge tab goes to krisfricke.github.io.
- The **−/+** control bottom-right sets page size; 100% is true printed size.
- Rest the pointer on a picture and it grows (slowly, then faster) to its full size; click early to jump there, click again to close.
- On mouse devices the pointer is a bee; hold still over a page for two seconds and she lands.
