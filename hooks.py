import os, re

def _filename_to_title(src_path: str) -> str:
    base = os.path.splitext(os.path.basename(src_path))[0]
    # Turn "House_Falcrest" / "House-Falcrest" into "House Falcrest"
    title = re.sub(r'[_\-]+', ' ', base).strip()
    title = re.sub(r'\s+', ' ', title)
    return title

def on_page_markdown(markdown, page, config, files):
    """
    Force page.title to come from the filename, not the first H1 or front-matter.
    Lets you keep Obsidian tag lines like "#npc #coven" at the top without affecting titles.
    """
    page.title = _filename_to_title(page.file.src_path)
    return markdown
