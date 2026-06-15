# Skillify Documentation Site

This directory contains the [Docusaurus 3](https://docusaurus.io/) documentation site for skillify, deployed to GitHub Pages at [nickommen.github.io/skillify](https://nickommen.github.io/skillify/).

## Prerequisites

- Node.js 20+
- npm

## Local Development

```bash
cd website
npm install
npm start
```

This starts a local dev server at `http://localhost:3000/skillify/`. Changes are reflected live without restarting.

## Build

```bash
npm run build
```

Generates static output in `build/`. To preview the production build locally:

```bash
npm run serve
```

## Deployment

Deployment is automatic via GitHub Actions on every push to `main` that changes files under `website/`. See [`.github/workflows/deploy-docs.yml`](../.github/workflows/deploy-docs.yml).

Pull requests that touch `website/` run a build + link check via [`.github/workflows/test-docs.yml`](../.github/workflows/test-docs.yml).

## Adding Blog Posts

Create a directory under `blog/` named `YYYY-MM-DD-slug/` with an `index.md` file:

```markdown
---
title: Your Post Title
authors:
  - name: Your Name
    url: https://github.com/yourhandle
tags: [tag1, tag2]
---

Summary paragraph shown on the blog index.

{/* truncate */}

Full post content below the fold.
```

## Adding Documentation Pages (Future)

When documentation pages are needed:

1. Set `docs: {}` (instead of `false`) in `docusaurus.config.js`
2. Create a `docs/` directory with markdown files
3. Create a `sidebars.js` to configure navigation
4. Add a Docs link to the navbar in `docusaurus.config.js`

## Project Structure

```
website/
  blog/                     # Blog posts (YYYY-MM-DD-slug/index.md)
  src/
    css/custom.css           # Theme color overrides
    pages/
      index.js               # Landing page
      index.module.css       # Landing page styles
  static/
    img/                     # Static images (SVG banners)
    .nojekyll                # Disable Jekyll on GitHub Pages
  docusaurus.config.js       # Site configuration
  package.json               # Node.js dependencies
```
