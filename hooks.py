# hooks.py
import os, re
from urllib.parse import urlparse

GENERIC = {"overview", "index", "home"}

def _filename_to_title(src_path: str) -> str:
    base = os.path.splitext(os.path.basename(src_path))[0]
    title = re.sub(r'[_\-]+', ' ', base).strip()
    title = re.sub(r'\s+', ' ', title)
    return title

def _is_tag_line(line: str) -> bool:
    tokens = line.strip().split()
    return bool(tokens) and all(t.startswith("#") and not t.startswith("# ") for t in tokens)

# ---------------- Obsidian [[Wiki Links]] ----------------

# [[Target]] | [[Target|Label]] | [[Folder/Sub Page]] | [[Page#Section]] | [[Page|Nice Label#Section]]
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]")

def _base_path_from_site_url(config) -> str:
    """Extract '/terrondar-wiki/' from site_url if set, otherwise '/'."""
    site_url = (config or {}).get('site_url') or ""
    path = urlparse(site_url).path or "/"
    if not path.endswith("/"):
        path += "/"
    return path

def _build_wiki_map(files):
    """
    Build maps to resolve [[Title]] -> 'Folder/Title' by scanning all markdown files.
    - name_map: 'Title' (basename, case-insensitive) -> 'Folder/Title' (without .md)
    - path_set: full logical paths (without .md), case-insensitive, for [[Folder/Title]]
    """
    name_map = {}
    path_set = set()
    for f in files:
        # Only consider markdown content files from /docs
        if getattr(f, 'src_path', '').lower().endswith('.md'):
            logical = f.src_path[:-3]  # strip .md
            path_set.add(logical.lower())
            base = os.path.basename(logical)
            # First one wins if duplicates; adjust if you prefer last wins
            name_map.setdefault(base.lower(), logical)
    return name_map, path_set

def _resolve_wiki_href(target: str, anchor: str | None, name_map, path_set, base_path: str) -> str:
    """
    Resolve an Obsidian target to an absolute href under the site root:
      - If target includes '/', treat as folder-qualified; use as-is if exists.
      - Else, find by basename via name_map.
      - Always emit directory-URLs style with trailing '/'.
      - Prepend base_path (e.g., '/terrondar-wiki/').
    """
    t = target.strip().replace("\\", "/")
    if t.lower().endswith(".md"):
        t = t[:-3]

    # If user wrote Folder/Page, honor it when it exists
    logical = None
    if "/" in t and t.lower() in path_set:
        logical = t
    else:
        # Lookup by basename (e.g., 'Contrena' -> 'Locations/Contrena')
        logical = name_map.get(t.lower())

    # Fallback: if not found, link to the literal text (still absolute to site root to avoid nesting)
    if not logical:
        href = t
    else:
        href = logical

    # Directory URLs: add trailing slash
    if not href.endswith("/"):
        href += "/"

    # Prepend base path for GitHub Pages project sites
    href = f"{base_path}{href.lstrip('/')}"

    # Anchor support
    if anchor:
        href = f"{href}#{anchor.strip()}"
    return href

def _replace_wiki_links(markdown: str, files, config) -> str:
    base_path = _base_path_from_site_url(config)
    name_map, path_set = _build_wiki_map(files)

    def _repl(m: re.Match):
        target = m.group(1).strip()
        anchor = m.group(2).strip() if m.group(2) else None
        label  = m.group(3).strip() if m.group(3) else target
        href = _resolve_wiki_href(target, anchor, name_map, path_set, base_path)
        return f"[{label}]({href})"

    return WIKI_LINK_RE.sub(_repl, markdown)

# ---------------- MkDocs hook ----------------

def on_page_markdown(markdown, page, config, files):
    """
    1) Force page meta title and visible H1 to the filename (humanized).
    2) Keep leading tag lines visible but never as titles.
    3) Convert Obsidian [[Wiki Links]] into absolute links to the correct page.
    """
    desired = _filename_to_title(page.file.src_path)

    # Convert [[Wiki Links]] first (so the rewritten markdown gets proper links)
    markdown = _replace_wiki_links(markdown, files, config)

    # Rewrite markdown so the first *content* H1 matches `desired`
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
    # Meta title for Material / breadcrumbs
    page.title = desired

    # Always make the first visible H1 our desired title
    new.append(f"# {desired}")
    new.append("")

    # Re-add tag lines under the title
    new.extend(tag_lines)
    if tag_lines:
        new.append("")

    # Skip old first H1 if it doesn't match
    rest_start = j
    if first_h1_idx is not None:
        if first_h1_text.lower() in GENERIC or first_h1_text != desired:
            rest_start = first_h1_idx + 1

    if rest_start < len(lines) and lines[rest_start].strip():
        new.append("")

    new.extend(lines[rest_start:])
    return "\n".join(new).rstrip() + "\n"

