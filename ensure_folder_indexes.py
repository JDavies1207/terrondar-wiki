import os
from pathlib import Path

DOCS = Path("docs")

TEMPLATE = """# {title}

Browse the {title} section using the sidebar.
"""

def needs_index(dirpath: Path) -> bool:
    if not dirpath.is_dir():
        return False
    has_md = any(p.suffix.lower() == ".md" and p.name.lower() != "index.md" for p in dirpath.iterdir())
    has_index = (dirpath / "index.md").exists()
    return has_md and not has_index

def title_from_folder(dirpath: Path) -> str:
    return dirpath.name.replace("_", " ").replace("-", " ").strip()

def main():
    created = 0
    for root, dirs, files in os.walk(DOCS):
        d = Path(root)
        if needs_index(d):
            title = title_from_folder(d)
            idx = d / "index.md"
            idx.write_text(TEMPLATE.format(title=title), encoding="utf-8")
            created += 1
            print(f"Created {idx}")
    print(f"Done. Created {created} index.md file(s).")

if __name__ == "__main__":
    main()
