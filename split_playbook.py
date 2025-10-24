import re, os, unicodedata
from pathlib import Path
import yaml

SRC = Path("playbook.md")
if not SRC.exists():
    raise SystemExit("❌ playbook.md niet gevonden in deze map.")

OUT = Path("site_mkdocs")
DOCS = OUT / "docs"
DOCS.mkdir(parents=True, exist_ok=True)

text = SRC.read_text(encoding="utf-8").strip()

# Split op H1 koppen
blocks = re.split(r"(?m)^#\s+", text)
if blocks and blocks[0].strip() == "":
    blocks = blocks[1:]

def slugify(s: str) -> str:
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode('ascii')
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', s).strip().lower()
    s = re.sub(r'\s+', '-', s)
    return s or 'sectie'

nav = []
addenda = []

for block in blocks:
    lines = block.splitlines()
    if not lines:
        continue
    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip()

    m_h = re.match(r"Hoofdstuk\s+(\d{1,2})\b[:,\-]?\s*(.*)", title, re.I)
    m_a = re.match(r"Addendum\s+([A-Z])\b[:,\-]?\s*(.*)", title, re.I)

    if m_h:
        num = int(m_h.group(1))
        rest = m_h.group(2).strip() if m_h.group(2) else ""
        fn = f"{num:02d}_{slugify(rest) or 'hoofdstuk'}.md"
        path = DOCS / fn
        nav.append({f"Hoofdstuk {num}: {rest}".strip(): fn})
        anchor = f'<a id="hoofdstuk-{num}"></a>\n'
    elif m_a:
        letter = m_a.group(1).upper()
        rest = (m_a.group(2) or "").strip()
        subdir = DOCS / "addenda"
        subdir.mkdir(exist_ok=True)
        fn = f"addendum_{letter.lower()}_{slugify(rest) or 'addendum'}.md"
        path = subdir / fn
        addenda.append({f"Addendum {letter}: {rest}".strip(): f"addenda/{fn}"})
        anchor = f'<a id="addendum-{letter.lower()}"></a>\n'
    else:
        # Intro / Overzicht
        fn = f"{slugify(title)}.md"
        path = DOCS / fn
        nav.append({title: fn})
        anchor = ""

    # schrijf bestand
    path.write_text(f"# {title}\n\n{anchor}{body}\n", encoding="utf-8")

# mkdocs.yml opbouwen
mk = {
    "site_name": "Belsberg Sales Playbook",
    "theme": {
        "name": "material",
        "features": [
            "navigation.top",
            "navigation.sections",
            "search.highlight",
            "content.code.copy"
        ],
        "palette": { "scheme": "default", "primary": "custom", "accent": "custom" },
        "font": { "text": "Space Grotesk" }
    },
    "extra_css": ["styles/brand.css"],
    "markdown_extensions": [
        { "toc": { "permalink": True } },
        "admonition", "tables", "attr_list", "footnotes", "def_list"
    ],
    "nav": nav + ([{ "Addenda": addenda }] if addenda else [])
}

(OUT / "mkdocs.yml").write_text(
    yaml.dump(mk, sort_keys=False, allow_unicode=True),
    encoding="utf-8"
)

# branding CSS
styles = DOCS / "styles"
styles.mkdir(parents=True, exist_ok=True)
(styles / "brand.css").write_text("""
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
:root{
  --belsberg-livid:#4C717A;
  --belsberg-sky:#7DB5C3;
  --belsberg-navy:#003D50;
  --belsberg-lime:#D2F8C0;
  --belsberg-lav:#B0A1F9;
  --md-primary-fg-color: var(--belsberg-livid);
  --md-accent-fg-color:  var(--belsberg-sky);
}
.md-typeset { font-family: 'Space Grotesk', system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
.md-typeset h1, .md-typeset h2, .md-typeset h3 { color: var(--belsberg-livid); }
a { color: var(--belsberg-livid); }
""", encoding="utf-8")

print("✅ Klaar. Ga verder met:")
print("   cd site_mkdocs")
print("   mkdocs serve   (lokaal bekijken)")
print("   mkdocs gh-deploy  (deploy naar GitHub Pages)")
