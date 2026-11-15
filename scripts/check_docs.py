import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
pages = [*ROOT.glob("README*.md"), *ROOT.joinpath("docs").rglob("*.md")]
bad = []
for page in pages:
    for link in re.findall(r"\]\(([^)\s]+)\)", page.read_text()):
        relative = link.split("#", 1)[0]
        if relative and not relative.startswith(("http://", "https://", "mailto:")):
            if not page.parent.joinpath(relative).exists():
                bad.append(f"{page.relative_to(ROOT)}: {relative}")
if bad:
    raise SystemExit("\n".join(bad))
print(f"Checked local links in {len(pages)} Markdown files")
