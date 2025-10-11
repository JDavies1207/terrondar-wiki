# hooks.py
import os, re

GENERIC = {"overview", "index", "home"}

def _filename_to_title(src_path: str) -> str:
    base = os.path.splitext(os.path.basename(src_path))[0]
    title = re.sub(r'[_\-]+', ' ', base).strip()
    title = re.sub(r'\s+', ' ', title)
    return title

def _is_tag_line(line: str) -> bool:
    # Lines like "#npc #coven" or "#Falcrest" (no space after '#') count as tag-only lines.
    tokens = line.strip().split()
    return bool(tokens) and all(t.startswith("#") and not t.startswith("# ") for t in tokens)

def on_page_markdown(markdown, page, config, files):
    """Force the display title to the filename and ensure the first visible H1 matches it.
    - Keeps leading Obsidian tag lines (#npc #coven).
    - Inserts '# <filename>' as the first H1 if none exists.
    - If the first H1 is generic (Overview/Index/Home) or wrong, replace it.
    """
    desired = _filename_to_title(page.file.src_path)

    # 1) Set MkDocs/Material page title used in header, breadcrumbs, etc.
    page.title = desired

    # 2) Rewrite markdown so the first *content* H1 matches `desired`
    lines = markdown.splitlines()

    # skip leading blanks
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1

    # gather leading tag-only lines
    j = i
    tag_lines = []
    while j < len(lines) and _is_tag_line(lines[j]):
        tag_lines.append(lines[j])
        j += 1

    # find first real H1 AFTER tag lines ("# Heading" with a space)
    first_h1_idx = None
    first_h1_text = ""
    for k in range(j, len(lines)):
        m = re.match(r'^\s*#\s+(.*)$', lines[k])
        if m:
            first_h1_idx = k
            first_h1_text = m.group(1).strip()
            break

    new = []

    # Always make the first visible H1 our desired title
    new.append(f"# {desired}")
    new.append("")

    # Re-add tag lines under the title (keeps them visible, but no longer hijack the title)
    new.extend(tag_lines)
    if tag_lines:
        new.append("")

    # Build the rest of the document:
    # - start from j (after tag lines)
    # - drop the original first H1 if it existed (to avoid duplicate titles),
    #   or keep it if it was already the desired title (rare)
    rest_start = j
    if first_h1_idx is not None:
        # if it wasn't already the desired title or a perfect match, drop it
        if first_h1_text.lower() in GENERIC or first_h1_text != desired:
            rest_start = first_h1_idx + 1  # skip the old H1 line
        # else: keep it (it already matches), but that would duplicate, so still skip it

    # ensure a blank after our inserted H1/tag block if the next line isn't blank
    if rest_start < len(lines) and lines[rest_start].strip():
        new.append("")

    new.extend(lines[rest_start:])

    # Return modified markdown
    return "\n".join(new).rstrip() + "\n"
