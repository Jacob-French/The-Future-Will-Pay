# The Future Will Pay — reader

Open `index.html` in a browser. Turn pages with ← →, space, a click/tap on the right or left of the
page, a swipe, or a scroll. Press **C** (or the ☰ button) for the chapter list, text size and version.
Your place is remembered separately for each version.

## Versions
- `versions/v1/` — the original draft, untouched.
- `versions/v2/` — the revised text (see `notes.md` for every change and why).

Pick a version on the title page or in the chapter panel. Switching from the panel keeps you on the
same chapter and roughly the same place, so you can compare the two. To start a new version, copy the
newest folder (e.g. `cp -r versions/v2 versions/v3`), edit it, and optionally add a `version.json`
with a `label` and `note`.

## How it's put together
- `versions/<id>/*.md` — the story, one Markdown file per chapter, read in filename order.
- `book.json` — title and subtitle.
- `build.py` — compiles every version into `story.js`. Run `python3 build.py` after editing a chapter.
- `index.html` — the reader. It paginates automatically to the window size, so chapters can be any length.
- `notes.md` — editorial notes for the v1 → v2 revision.
- `planning/` — notes, world bible, story and chapter plans, revision notes.

Chapter syntax is in the docstring at the top of `build.py` (front matter for title/part/label,
`*italics*`, `* * *` scene breaks, `>` quotes/epigraphs, `::` centred signs).
