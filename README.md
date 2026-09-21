# My Personal Website

![Build Status](https://github.com/aav7fl/website/actions/workflows/github-pages.yml/badge.svg)

[![Kyle Niewiada logo](https://user-images.githubusercontent.com/3487107/63467880-73b38880-c434-11e9-97d9-46c6d3e2f1ec.png)](https://www.kyleniewiada.org/)

https://www.kyleniewiada.org/

This is my personal website that I tweak and write about projects I have worked on.

**Check out [the repo Wiki](https://github.com/aav7fl/website/wiki) for the latest documentation and information.**

## Features
- Mobile responsive
- Uses modern HTML5 and CSS3
- AMP validated ([Accelerated Mobile Pages](https://amp.dev/))
- Ready for GitHub Actions continuous integration
- Basic Testing

---

`main` [default] branch contains the website source code.

`gh-pages` branch contains the generated website.

## Test

`bundle exec rake test`

## Develop Locally

- Open in VSCode
- Open in dev container
- After container is built run `bundle exec rake`

## Diagrams

Write Mermaid in a fenced ` ```mermaid ` block. `bundle exec rake` renders it to
a static SVG under `assets/img/<YEAR>/<MONTH>/`, catalogued in
`_data/mermaid.json`, and swaps the block for an `<img>` — no Mermaid
JavaScript is served, and the AMP layout gets a valid `<amp-img>`.

- Commit the generated SVGs and `_data/mermaid.json` alongside the post.
- Adding, editing, and deleting diagrams all sync automatically on build.
- Alt text comes from the diagram's own `accDescr:` (or `accTitle:`).
- CI only verifies (`npm run mermaid:check`); it never renders.

Re-rendering reports whether a diagram changed structurally (labels, connectors,
shapes) or only cosmetically, so a few pixels of font drift stays quiet while a
moved arrow prints `REVIEW:` and lists the file. Upgrading `mermaid-cli` does not
re-render on its own; run `npm run mermaid:force` if you want every diagram on
the new renderer, and review what it reports.