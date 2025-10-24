"""
Belsberg Playbook Build Script v3
---------------------------------
Bron = Word (.docx)
Output = Markdown + MkDocs site (+ PDF optioneel)
Features:
- verwijdert handmatige Inhoudsopgave
- maakt hoofdstuk/addendum anchors
- linkt automatisch: "Zie Hoofdstuk X" en "Zie Addendum B, Script E37–E38"
- bouwt site en pusht naar GitHub Pages
"""

import re, os, unicodedata, subprocess, shutil
from pathlib import Path
import yaml

# === CONFIG ===
DOCX_SRC = Path("~/Desktop/Belsberg Playbook/BELSBERG SALES PLAYBOOK FINAL V3.0.docx").expanduser()
MD_FILE = Path("playbook.md")
OUT = Path("site_mkdocs")
DOCS = OUT / "docs"
PDF_FILE = Path("Belsberg_Playbook_v3.pdf")  # optioneel

# === STEP 1: Convert Word -> Markdown ===
print("📄 Converting Word → Markdown...")
subprocess.run(["pandoc", str(DOCX_SRC), "-t", "gfm", "-o", str(MD_FILE)], check=True)

text = MD_FILE.read_text(encoding="utf-8")

# Remove "Inhoudsopgave"
text = re.sub(r'(?ms)^(#{1,3})\s*Inhoudsopgave\s*?\n.*?(?=^#\s|\Z)', '', text, flags=re.IGNORECASE).strip()

# === STEP 2: Split per Hoofdstuk / Addendum ===
print("✂️  Splitting sections...")

if OUT.exists():
    shutil.rmtree(OUT)
DOCS.mkdir(parents=True, exist_ok=True)

blocks = re.split(r"(?m)^#\s+", text)
if blocks and not blocks[0].strip():
    blocks = blocks[1:]

def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode('ascii')
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', s).strip().lower()
    s = re.sub(r'\s+', '-', s)
    return s or 'sectie'

nav, addenda_nav, chapter_map, addendum_map = [], [], {}, {}

for block in blocks:
    lines = block.splitlines()
    if not lines: continue
    title, body = lines[0].strip(), "\n".join(lines[1:]).strip()
    m_h = re.match(r"Hoofdstuk\s+(\d{1,2})\b[:,\-]?\s*(.*)", title, re.I)
    m_a = re.match(r"Addendum\s+([A-Z])\b[:,\-]?\s*(.*)", title, re.I)

    if m_h:
        num, rest = int(m_h.group(1)), (m_h.group(2) or "").strip()
        fn = f"{num:02d}_{slugify(rest)}.md"
        chapter_map[num] = fn
        path = DOCS / fn
        nav.append({f"Hoofdstuk {num}: {rest}".strip(): fn})
        anchor = f'<a id="hoofdstuk-{num}"></a>\n'
        content = f"# {title}\n\n{anchor}{body}\n"

    elif m_a:
        letter, rest = m_a.group(1).upper(), (m_a.group(2) or "").strip()
        subdir = DOCS / "addenda"
        subdir.mkdir(exist_ok=True)
        fn = f"addendum_{letter.lower()}_{slugify(rest)}.md"
        rel = f"addenda/{fn}"
        addendum_map[letter] = rel
        path = subdir / fn
        addenda_nav.append({f"Addendum {letter}: {rest}".strip(): rel})
        anchor = f'<a id="addendum-{letter.lower()}"></a>\n'
        content = f"# {title}\n\n{anchor}{body}\n"
    else:
        fn = f"{slugify(title)}.md"
        path = DOCS / fn
        nav.append({title: fn})
        content = f"# {title}\n\n{body}\n"

    path.write_text(content, encoding="utf-8")

# === STEP 3: Linkify references ===
print("🔗 Linking internal references...")

def linkify(s):
    # Hoofdstukken
    s = re.sub(
        r'(?i)\b(Zie)\s+Hoofdstuk\s+(\d{1,2})\b',
        lambda m: f"[{m.group(0)}]({chapter_map.get(int(m.group(2)), '')})"
                  if chapter_map.get(int(m.group(2))) else m.group(0),
        s
    )

    # Addenda + scripts (E37–E38 of E37, E41)
    def repl_add(m):
        letter, tail = m.group(2).upper(), m.group(3) or ""
        fn = addendum_map.get(letter)
        if not fn:
            return m.group(0)
        base = f"[{m.group(1)} Addendum {letter}]({fn})"
        # Check for script numbers in tail
        matches = re.findall(r'E\d+', tail, flags=re.I)
        if matches:
            links = []
            for script_id in matches:
                slug = f"#script-{script_id.lower()}"
                links.append(f"[{script_id}]({fn}{slug})")
            joined = ", ".join(links)
            return f"{base}, {joined}"
        return base + tail

    s = re.sub(r'(?i)\b(Zie)\s+Addendum\s+([A-Z])\b(\s*,\s*[^\n\.]+)?', repl_add, s)
    return s

for p in DOCS.rglob("*.md"):
    t = p.read_text(encoding="utf-8")
    p.write_text(linkify(t), encoding="utf-8")

# === STEP 4: mkdocs.yml ===
print("⚙️  Building mkdocs.yml...")

mk = {
    "site_name": "Belsberg Sales Playbook",
    "theme": {
        "name": "material",
        "features": [
            "navigation.instant", "navigation.sections", "navigation.expand",
            "search.highlight", "toc.follow", "toc.integrate"
        ],
        "palette": {"scheme": "default", "primary": "custom", "accent": "custom"},
        "font": {"text": "Space Grotesk"}
    },
    "extra_css": ["styles/brand.css"],
    "markdown_extensions": [
        {"toc": {"permalink": True}},
        "admonition", "tables", "attr_list", "footnotes", "def_list",
        "sane_lists", "smarty", "md_in_html"
    ],
    "nav": nav + ([{"Addenda": addenda_nav}] if addenda_nav else [])
}

(OUT / "mkdocs.yml").write_text(
    yaml.dump(mk, sort_keys=False, allow_unicode=True), encoding="utf-8"
)

# === STEP 5: CSS branding ===
styles = DOCS / "styles"
styles.mkdir(parents=True, exist_ok=True)
(styles / "brand.css").write_text("""
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap');
:root{
  --belsberg-livid:#4C717A; --belsberg-sky:#7DB5C3; --belsberg-navy:#003D50;
  --belsberg-lime:#D2F8C0; --belsberg-lav:#B0A1F9;
  --md-primary-fg-color: var(--belsberg-livid);
  --md-accent-fg-color: var(--belsberg-sky);
}
.md-typeset { font-family:'Space Grotesk',system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
.md-typeset h1,.md-typeset h2,.md-typeset h3{ color: var(--belsberg-livid) }
a{ color: var(--belsberg-livid) }
""", encoding="utf-8")

# === STEP 6: Build & Deploy site ===
print("🌐 Deploying to GitHub Pages...")
subprocess.run(["mkdocs", "gh-deploy"], cwd=OUT, check=True)

# === STEP 7: Generate PDF (optional) ===
# Uncomment als Pandoc PDF gewenst:
# subprocess.run(["pandoc", str(DOCX_SRC), "-o", str(PDF_FILE), "--pdf-engine=wkhtmltopdf", "-s", "--toc"], check=True)

print("\n✅ Build completed!")
print(f"→ Markdown: {MD_FILE}")
print(f"→ Site: {OUT}")
print(f"→ Live: https://kaap11.github.io/playbook_test/")

