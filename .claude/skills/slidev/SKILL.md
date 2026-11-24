---
name: slidev
description: Creates and runs developer slide decks with Slidev — Markdown slides with code highlighting, animations, diagrams, presenter notes, and PDF/PPTX export. Use for technical talks, code walkthroughs, workshops, or "/slidev".
allowed-tools: Read, Grep, Glob, Write, Edit, WebFetch, Bash(pnpm *), Bash(npx slidev *), Bash(ls *)
---

# Slidev

Slidev is a web-based slide tool built on Vite, Vue, and Markdown. It suits talks with live code, syntax-highlighted snippets, diagrams, and math.

For any detail not on this page, fetch the official docs with `WebFetch` from `https://sli.dev` (start at `https://sli.dev/guide/`). Do not guess syntax.

## Workflow

1. **Set up.** In an empty folder, run `pnpm create slidev`. In an existing deck, use its `slides.md`.
2. **Write the deck** in `slides.md`, with the syntax below. Keep one idea on each slide. Put the speaking text in presenter notes, not on the slide.
3. **Check it.** Run `pnpm run dev`, and confirm that the slides load at `http://localhost:3030`.
4. **Export or build, if asked.** `pnpm run export` writes a PDF to the project root; it needs `pnpm add -D playwright-chromium`, so install that first if the export fails with a browser error. `pnpm run build` makes a static SPA.

## Basic syntax

```md
---
theme: default
title: My Presentation
---

# First Slide

Content here

---

# Second Slide

More content

<!--
Presenter notes go here
-->
```

- `---` separates slides.
- The first frontmatter is the headmatter: the configuration of the deck. Each later frontmatter configures one slide.
- An HTML comment at the end of a slide holds its presenter notes.

## Feature cheat sheet

### Code and editor

| Feature | Usage |
|---------|-------|
| Line highlighting | `` ```ts {2,3} `` |
| Highlighting by click | `` ```ts {1\|2-3\|all} `` |
| Line numbers | `lineNumbers: true`, or `{lines:true}` |
| Scrollable code | `{maxHeight:'100px'}` |
| Code tabs | `::code-group` (needs `comark: true`) |
| Monaco editor | `` ```ts {monaco} `` |
| Runnable code | `` ```ts {monaco-run} `` |
| Edit a file | `<<< ./file.ts {monaco-write}` |
| Code animation | `` ````md magic-move `` |
| TypeScript types | `` ```ts twoslash `` |
| Import a snippet | `<<< @/snippets/file.js` |

### Diagrams and math

| Feature | Usage |
|---------|-------|
| Mermaid | `` ```mermaid `` |
| PlantUML | `` ```plantuml `` |
| LaTeX | `$inline$` or `$$block$$` |

### Layout and style

| Feature | Usage |
|---------|-------|
| Canvas size | `canvasWidth`, `aspectRatio` |
| Zoom a slide | `zoom: 0.8` |
| Scale elements | `<Transform :scale="0.5">` |
| Layout slots | `::right::`, `::default::` |
| Scoped CSS | `<style>` in the slide |
| Global layers | `global-top.vue`, `global-bottom.vue` |
| Draggable elements | `v-drag`, `<v-drag>` |
| Icons | `<mdi-icon-name />` |

### Animation and interaction

| Feature | Usage |
|---------|-------|
| Click animations | `v-click`, `<v-clicks>` |
| Rough markers | `v-mark.underline`, `v-mark.circle` |
| Drawing mode | Press `C`, or configure `drawings:` |
| Direction styles | `forward:delay-300` |
| Highlight in notes | `[click]` in the notes |

### Syntax extensions

| Feature | Usage |
|---------|-------|
| Comark syntax | `comark: true` + `{style="color:red"}` |
| Block frontmatter | `` ```yaml `` instead of `---` |
| Import slides | `src: ./other.md` |
| Merged frontmatter | The main entry wins |

### Presenter and recording

| Feature | Usage |
|---------|-------|
| Recording | Press `G` for the camera |
| Timer | `duration: 30min`, `timer: countdown` |
| Remote control | `slidev --remote` |
| Ruby text | `notesAutoRuby:` |

### Export and build

| Feature | Usage |
|---------|-------|
| Export | `slidev export` (PDF, PPTX, PNG) |
| Build and deploy | `slidev build` |
| PDF in the build | `download: true` |
| Cache remote images | Automatic |
| OG image | `seoMeta.ogImage`, or `og-image.png` |
| SEO tags | `seoMeta:` |

### Editor and tools

| Feature | Usage |
|---------|-------|
| Side editor | Click the edit icon |
| VS Code extension | `antfu.slidev` |
| Prettier | `prettier-plugin-slidev` |
| Eject a theme | `slidev theme eject` |
| Slide hooks | `onSlideEnter()`, `onSlideLeave()` |
| Navigation API | `$nav`, `useNav()` |

## Layouts

| Layout | Purpose |
|--------|---------|
| `cover` | Title slide |
| `center` | Centered content |
| `default` | Standard slide |
| `two-cols` | Two columns (use `::right::`) |
| `two-cols-header` | Header + two columns |
| `image`, `image-left`, `image-right` | Image layouts |
| `iframe`, `iframe-left`, `iframe-right` | Embedded URLs |
| `quote` | Quotation |
| `section` | Section divider |
| `fact`, `statement` | A number or a statement |
| `intro`, `end` | First and last slides |

## Resources

- Documentation: https://sli.dev
- Theme gallery: https://sli.dev/resources/theme-gallery
- Showcases: https://sli.dev/resources/showcases
