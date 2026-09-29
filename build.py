#!/usr/bin/env python3
"""
Compile the story into story.js, which index.html reads.

    python3 build.py

Versions
--------
Each folder in versions/ is one version of the book (v1, v2, ...), read in
name order. The reader lets you switch between them. A version folder may hold
an optional version.json:

    {"label": "Revised", "note": "Editorial pass: ..."}

If there is no versions/ folder, chapters/ is used as a single version.

Chapter files
-------------
Chapter files are read in filename order (01-..., 02-..., ...).
Each file may start with a small front-matter block:

    ---
    title: The Standby
    part: Part One · The Draw      (optional; shown when the part changes)
    label: Prologue                (optional; replaces "Chapter N")
    ---

Body syntax (deliberately tiny):
    blank line          -> new paragraph
    *italic*  **bold**
    * * *               -> scene break
    > quoted lines      -> block quote (an epigraph if it comes before any prose)
    > — Attribution     -> right-aligned attribution inside a quote
    :: CENTERED LINE    -> centred sign / poster / placard text
    ### Heading         -> small section heading
Straight quotes and "--" are converted to typographic quotes and dashes.
"""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
VERSIONS = ROOT / "versions"
CHAPTERS = ROOT / "chapters"
OUT = ROOT / "story.js"
BOOK = ROOT / "book.json"


def typographic(s: str) -> str:
    s = s.replace("...", "…").replace("--", "—")
    out = []
    n = len(s)
    for i, c in enumerate(s):
        if c not in "\"'":
            out.append(c)
            continue
        j = i - 1
        while j >= 0 and s[j] in "*_":
            j -= 1
        prev = s[j] if j >= 0 else " "
        nxt = s[i + 1] if i + 1 < n else " "
        opening = prev.isspace() or prev in "([{" or (
            prev in "—–" and (nxt.isalnum() or nxt in "*_…")
        )
        if c == "'" and opening and nxt.isdigit():  # '90s
            opening = False
        if c == '"':
            out.append("“" if opening else "”")
        else:
            out.append("‘" if opening else "’")
    s = "".join(out)
    # keep an em dash glued to the word before it (no line break before a dash)
    return re.sub(r"(?<=\S)—", "⁠—", s)


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = typographic(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    return s


def parse_front(text: str):
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        text = text[m.end():]
    return meta, text


def render(body: str):
    blocks = re.split(r"\n[ \t]*\n", body.strip())
    out, seen_prose = [], False
    for b in blocks:
        b = b.strip("\n")
        if not b.strip():
            continue
        lines = [l.rstrip() for l in b.split("\n")]
        first = lines[0].strip()
        if re.fullmatch(r"(\*\s*){3}|⁂|~~~", b.strip()):
            out.append('<div class="brk">⁂</div>')
        elif all(l.lstrip().startswith(">") for l in lines):
            cls = "doc" if seen_prose else "epi"
            paras, cur, attr = [], [], None
            for l in lines:
                t = l.lstrip()[1:].strip()
                if not t:
                    if cur:
                        paras.append(cur)
                        cur = []
                elif re.match(r"^(—|--)\s*", t):
                    attr = re.sub(r"^(—|--)\s*", "", t)
                else:
                    cur.append(t)
            if cur:
                paras.append(cur)
            inner = "".join("<p>" + "<br>".join(inline(x) for x in p) + "</p>" for p in paras)
            if attr:
                inner += '<span class="attr">' + inline(attr) + "</span>"
            out.append(f'<blockquote class="{cls}">{inner}</blockquote>')
        elif all(l.lstrip().startswith("::") for l in lines):
            inner = "<br>".join(inline(l.lstrip()[2:].strip()) for l in lines)
            out.append(f'<div class="sign">{inner}</div>')
        elif first.startswith("### "):
            out.append("<h3>" + inline(first[4:]) + "</h3>")
            rest = " ".join(l.strip() for l in lines[1:])
            if rest:
                out.append("<p>" + inline(rest) + "</p>")
                seen_prose = True
        else:
            text = " ".join(l.strip() for l in lines)
            cls = ' class="first"' if not seen_prose else ""
            out.append(f"<p{cls}>" + inline(text) + "</p>")
            seen_prose = True
    return "\n".join(out)


def build_chapters(folder: pathlib.Path):
    chapters, num, last_part = [], 0, None
    for f in sorted(folder.glob("*.md")):
        meta, body = parse_front(f.read_text(encoding="utf-8"))
        if meta.get("skip", "").lower() in ("yes", "true", "1"):
            continue
        label = meta.get("label")
        if not label:
            num += 1
            label = f"Chapter {num}"
        part = meta.get("part") or last_part
        words = len(re.findall(r"[A-Za-z0-9’']+", body))
        chapters.append({
            "file": f.name,
            "label": label,
            "title": meta.get("title", f.stem),
            "part": part or "",
            "partStart": bool(part) and part != last_part,
            "words": words,
            "html": render(body),
        })
        last_part = part
    return chapters


def main():
    book = {"title": "Untitled", "subtitle": "", "author": ""}
    if BOOK.exists():
        book.update(json.loads(BOOK.read_text(encoding="utf-8")))

    folders = []
    if VERSIONS.exists():
        folders = [d for d in sorted(VERSIONS.iterdir()) if d.is_dir()]
    if not folders and CHAPTERS.exists():
        folders = [CHAPTERS]

    versions = []
    for d in folders:
        info = {"label": "", "note": ""}
        vj = d / "version.json"
        if vj.exists():
            info.update(json.loads(vj.read_text(encoding="utf-8")))
        vid = d.name if d != CHAPTERS else "v1"
        chapters = build_chapters(d)
        versions.append({"id": vid, "label": info["label"], "note": info["note"], "chapters": chapters})
        total = sum(c["words"] for c in chapters)
        print(f"{vid}: {len(chapters)} chapters, {total:,} words" + (f"  ({info['label']})" if info["label"] else ""))

    book["versions"] = versions
    # the newest version is the default; "chapters" is kept for older readers
    book["defaultVersion"] = versions[-1]["id"] if versions else ""
    book["chapters"] = versions[-1]["chapters"] if versions else []
    OUT.write_text("window.STORY = " + json.dumps(book, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"{len(versions)} version(s) -> {OUT.name}")


if __name__ == "__main__":
    main()
