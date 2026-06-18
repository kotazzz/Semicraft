#!/usr/bin/env python3
"""Import MediaWiki XML export into Obsidian/Quartz content folder."""

import html
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
XML_PATH = ROOT / "Semicraft-20260618091159.xml"

NS = "{http://www.mediawiki.org/xml/export-0.11/}"

TITLE_TO_PATH: dict[str, str] = {
    "Заглавная страница": "index",
    "Заглавная страница/en": "en/index",
    "FAQ": "guides/FAQ",
    "Полезные ресурсы для декодирования": "guides/Декодирование",
    "Правила": "rules/Правила",
    "Сайт Semicraft": "site/Сайт Semicraft",
    "Аномалии": "anomalies/index",
    "Вирус": "anomalies/Вирус",
    "Armorstand": "anomalies/Armorstand",
    "Stars": "anomalies/Stars",
    "Игроки": "players/index",
}

SKIP_TITLES = {"Заглавная страница/ru"}

PLAYER_FILES: dict[str, str] = {
    "Bobbies1": "players/Bobbies1",
    "HanoiHaze": "players/HanoiHaze",
    "Jamer_77": "players/Jamer_77",
    "SlimeyPretty": "players/SlimeyPretty",
    "Voidwalker": "players/Voidwalker",
    "Nyrashine": "players/Nyrashine",
}


def decode(text: str) -> str:
    return html.unescape(text)


def slug_for_title(title: str) -> str:
    if title in TITLE_TO_PATH:
        return TITLE_TO_PATH[title]
    return title.replace(" ", "_")


def wiki_target_to_link(target: str) -> str:
    target = target.strip()
    target = re.sub(r"^Special:MyLanguage/", "", target)
    target = target.replace("_", " ")
    if target in TITLE_TO_PATH:
        return TITLE_TO_PATH[target]
    if target in PLAYER_FILES:
        return PLAYER_FILES[target]
    return slug_for_title(target)


def parse_template_params(inner: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for line in inner.strip().splitlines():
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        params[key.strip()] = value.strip()
    return params


def stub_callout(params: dict[str, str]) -> str:
    comment = params.get("комментарий", "Статья не завершена.")
    return f"> [!warning] Черновик\n> {comment}\n"


def entity_frontmatter(params: dict[str, str], tags: list[str]) -> str:
    title = params.get("название", "")
    lines = ["---"]
    if title:
        lines.append(f"title: {title}")
    lines.append("type: сущность")
    mapping = {
        "тип": "entity_type",
        "угроза": "threat",
        "поведение": "behavior",
        "особенности": "features",
        "изображение": "image",
        "здоровье": "health",
        "урон": "damage",
        "локация": "location",
    }
    for ru, en in mapping.items():
        if params.get(ru):
            lines.append(f"{en}: {params[ru]}")
    lines.append("draft: true")
    if tags:
        lines.append("tags:")
        for tag in tags:
            lines.append(f"  - {tag}")
    lines.append("---\n")
    return "\n".join(lines)


def entity_infobox(params: dict[str, str]) -> str:
    rows = []
    labels = {
        "название": "Название",
        "тип": "Тип",
        "угроза": "Угроза",
        "поведение": "Поведение",
        "особенности": "Особенности",
        "здоровье": "Здоровье",
        "урон": "Урон",
        "локация": "Локация",
    }
    for key, label in labels.items():
        if params.get(key):
            rows.append(f"| {label} | {params[key]} |")
    if not rows:
        return ""
    image = params.get("изображение")
    body = "\n".join(["| Поле | Значение |", "| --- | --- |", *rows])
    if image:
        caption = params.get("название", image)
        return f"![{caption}](images/{image.replace(' ', '%20')})\n\n{body}\n"
    return f"{body}\n"


def player_frontmatter(params: dict[str, str], era: str) -> str:
    name = params.get("имя") or params.get("никнейм", "")
    lines = ["---", f"title: {name}", "type: игрок"]
    mapping = {
        "никнейм": "nickname",
        "статус": "status",
        "роль": "role",
        "первое_появление": "first_seen",
        "группировка": "faction",
        "изображение": "skin",
    }
    for ru, en in mapping.items():
        if params.get(ru):
            lines.append(f"{en}: {params[ru]}")
    if era:
        lines.append(f"era: {era}")
    lines.extend(["tags:", "  - player", "  - lore", "---\n"])
    return "\n".join(lines)


POSITIONAL_IMAGE_PARAMS = {
    "мини", "mini", "thumb", "left", "right", "center", "centre", "безрамки", "none",
}


def convert_image(match: re.Match[str]) -> str:
    raw = match.group(1)
    parts = [p.strip() for p in raw.split("|")]
    filename = parts[0].replace("Файл:", "").replace("File:", "")
    caption = ""
    for part in parts[1:]:
        part_lower = part.lower()
        if not part or part_lower in POSITIONAL_IMAGE_PARAMS:
            continue
        if re.match(r"^\d+(px|x\d+|пкс)?$", part_lower):
            continue
        caption = part.strip("'\"")
        break
    alt = caption or filename
    safe_name = filename.replace(" ", "%20")
    return f"![{alt}](images/{safe_name})"


def convert_wikilink(match: re.Match[str]) -> str:
    raw = match.group(1)
    if "|" in raw:
        target, label = raw.split("|", 1)
    else:
        target, label = raw, raw
    if ":" in target and not target.startswith("Special:"):
        return match.group(0)
    link = wiki_target_to_link(target)
    return f"[[{link}|{label.strip()}]]"


def convert_external_link(match: re.Match[str]) -> str:
    url = match.group(1).strip()
    if url.startswith("[") or url.startswith("Special:"):
        return match.group(0)
    label = match.group(2).strip() if match.group(2) else url
    label = re.sub(r"'''|''|<u>|</u>", "", label)
    return f"[{label}]({url})"


def convert_heading(line: str) -> str:
    m = re.match(r"^(=+)\s*(.+?)\s*\1\s*$", line.strip())
    if not m:
        return line
    level = len(m.group(1))
    title = m.group(2).strip()
    return f"{'#' * min(level, 6)} {title}"


def convert_wikitable(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip().startswith("{|"):
            out.append(line)
            i += 1
            continue
        table_lines: list[str] = []
        while i < len(lines):
            table_lines.append(lines[i])
            if lines[i].strip() == "|}":
                i += 1
                break
            i += 1
        out.append(wikitable_to_markdown("\n".join(table_lines)))
    return "\n".join(out)


def wikitable_to_markdown(table: str) -> str:
    rows: list[list[str]] = []
    for line in table.splitlines():
        line = line.strip()
        if not line or line.startswith("{|") or line in ("|}", "|-", "|"):
            continue
        if line.startswith("!"):
            cells = [clean_cell(c) for c in re.split(r"!!", line.lstrip("!"))]
            rows.append(cells)
        elif line.startswith("|"):
            cells = [clean_cell(c) for c in line.lstrip("|").split("|")]
            rows.append(cells)
    rows = [r for r in rows if any(cell.strip() for cell in r)]
    if len(rows) < 1:
        return table
    width = max(len(r) for r in rows)
    header = rows[0]
    body = rows[1:]
    if len(header) < width:
        header += [""] * (width - len(header))
    md = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        padded = row + [""] * (width - len(row))
        md.append("| " + " | ".join(padded[:width]) + " |")
    return "\n".join(md) + "\n"


def clean_cell(text: str) -> str:
    text = decode(text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<translate>|</translate>", "", text)
    text = re.sub(r"style=\"[^\"]*\"", "", text)
    text = re.sub(r"colspan=\"[^\"]*\"", "", text)
    text = re.sub(r"'''([^']+)'''", r"**\1**", text)
    text = re.sub(r"''([^']+)''", r"*\1*", text)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text)
    text = convert_images_inline(text)
    text = convert_links_inline(text)
    return text.strip()


def convert_images_inline(text: str) -> str:
    return re.sub(r"\[\[(?:Файл|File):([^\]]+)\]\]", convert_image, text)


def convert_links_inline(text: str) -> str:
    text = re.sub(r"\[([^\s\]]+)\s+([^\]]+)\]", convert_external_link, text)
    text = re.sub(r"\[\[([^\]]+)\]\]", convert_wikilink, text)
    return text


def strip_translate(text: str) -> str:
    text = re.sub(r"<languages\s*/>", "", text)
    text = re.sub(r"<!--T:\d+-->", "", text)
    text = re.sub(r"<translate>|</translate>", "", text)
    text = re.sub(r"<nowiki>|</nowiki>", "", text)
    text = re.sub(r"<span[^>]*>|</span>", "", text)
    text = re.sub(r"<div[^>]*>|</div>", "", text)
    text = re.sub(r"<u>|</u>", "", text)
    return text


def convert_templates(text: str) -> tuple[str, dict]:
    meta: dict = {"tags": [], "draft": False, "frontmatter_extra": []}

    def repl_stub(m: re.Match[str]) -> str:
        meta["draft"] = True
        params = parse_template_params(m.group(1))
        meta["tags"].append("draft")
        return stub_callout(params) + "\n"

    def repl_entity(m: re.Match[str]) -> str:
        params = parse_template_params(m.group(1))
        meta["entity_params"] = params
        meta["tags"].extend(["anomaly", "entity"])
        meta["draft"] = True
        return entity_infobox(params)

    def repl_nav(_: re.Match[str]) -> str:
        return (
            "\n---\n\n## Навигация\n\n"
            "- [[index|Главная]]\n"
            "- [[anomalies/index|Аномалии]]\n"
            "- [[guides/FAQ|FAQ]]\n"
            "- [[players/index|Игроки]]\n"
            "- [[rules/Правила|Правила]]\n"
            "- [[site/Сайт Semicraft|Сайт Semicraft]]\n"
            "- [[guides/Декодирование|Инструменты декодирования]]\n"
        )

    def repl_service(_: re.Match[str]) -> str:
        meta["tags"].append("meta")
        return ""

    text = re.sub(r"\{\{Stub\|([^}]+)\}\}", repl_stub, text, flags=re.I)
    text = re.sub(r"\{\{Stub\}\}", repl_stub, text, flags=re.I)
    text = re.sub(r"\{\{Сущность\n(.*?)\n\}\}", repl_entity, text, flags=re.S)
    text = re.sub(r"\{\{Навигация\}\}", repl_nav, text)
    text = re.sub(r"\{\{Служебная страница\}\}", repl_service, text)
    text = re.sub(r"\[\[Категория:([^\]|]+)(?:\|[^\]]+)?\]\]", lambda m: "", text)
    return text, meta


def convert_bold_italic(text: str) -> str:
    text = re.sub(r"'''([^']+)'''", r"**\1**", text)
    text = re.sub(r"''([^']+)''", r"*\1*", text)
    return text


def convert_code(text: str) -> str:
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.S)
    return text


def convert_lists(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        if re.match(r"^# [^#]", line):
            line = re.sub(r"^# ", "1. ", line)
        out.append(line)
    return "\n".join(out)


def fix_broken_links(text: str) -> str:
    text = re.sub(
        r"\[([^\]]+)\]\(\[([^\]|]+)\|([^\]]+)\]\)",
        r"[[\2|\3]]",
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\(\[([^\]]+)\]\)",
        r"[[\2|\1]]",
        text,
    )
    return text


def wikitext_to_markdown(text: str) -> tuple[str, dict]:
    text = decode(text)
    text = strip_translate(text)
    text, meta = convert_templates(text)
    text = convert_wikitable(text)
    lines = []
    for line in text.splitlines():
        if line.strip().startswith("{|"):
            continue
        if line.strip() in ("|}", "|-", "|"):
            continue
        line = convert_heading(line)
        lines.append(line)
    text = "\n".join(lines)
    text = convert_code(text)
    text = convert_bold_italic(text)
    text = convert_images_inline(text)
    text = convert_links_inline(text)
    text = convert_lists(text)
    text = fix_broken_links(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n", meta


def extract_players(wikitext: str) -> dict[str, tuple[str, str, dict]]:
    """Return player name -> (era, description markdown, template params)."""
    text = decode(wikitext)
    text = strip_translate(text)
    players: dict[str, tuple[str, str, dict]] = {}
    era = ""
    for block in re.split(r"(?=\n== )", text):
        era_match = re.search(r"^== (.+?) ==\s*$", block, re.M)
        if era_match:
            era = era_match.group(1).strip()
        for match in re.finditer(
            r"=== (.+?) ===\s*\n(\{\{Игрок\n.*?\n\}\})(.*?)(?=\n=== |\n== |\Z)",
            block,
            re.S,
        ):
            name = match.group(1).strip()
            template = match.group(2)
            body = match.group(3).strip()
            params = parse_template_params(template.replace("{{Игрок", "").replace("}}", ""))
            body_md, _ = wikitext_to_markdown(body)
            players[name] = (era, body_md, params)
    return players


def build_entity_frontmatter(params: dict[str, str], tags: list[str]) -> dict:
    fm: dict = {"type": "сущность", "draft": True, "tags": sorted(set(tags))}
    if params.get("название"):
        fm["title"] = params["название"]
    mapping = {
        "тип": "entity_type",
        "угроза": "threat",
        "поведение": "behavior",
        "особенности": "features",
        "изображение": "image",
        "здоровье": "health",
        "урон": "damage",
        "локация": "location",
    }
    for ru, en in mapping.items():
        if params.get(ru):
            fm[en] = params[ru]
    return fm


def write_note(rel_path: str, body: str, frontmatter: Optional[dict] = None) -> None:
    path = CONTENT / f"{rel_path}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    if frontmatter:
        lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
        lines.append("---\n")
        parts.append("\n".join(lines))
    parts.append(body.strip() + "\n")
    path.write_text("\n".join(parts), encoding="utf-8")


def clear_old_content() -> None:
    for item in CONTENT.iterdir():
        if item.name in (".obsidian", "images"):
            if item.name == ".obsidian":
                continue
            continue
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            import shutil

            shutil.rmtree(item)
    (CONTENT / "images").mkdir(exist_ok=True)
    (CONTENT / "images" / ".gitkeep").write_text("", encoding="utf-8")


def parse_pages() -> dict[str, str]:
    tree = ET.parse(XML_PATH)
    pages: dict[str, str] = {}
    for page in tree.getroot().findall(f"{NS}page"):
        title = page.findtext(f"{NS}title", "")
        ns = page.findtext(f"{NS}ns", "0")
        if ns != "0" or title.startswith("Шаблон:"):
            continue
        if title in SKIP_TITLES:
            continue
        revision = page.find(f"{NS}revision")
        if revision is None:
            continue
        text_el = revision.find(f"{NS}text")
        if text_el is None or not text_el.text:
            continue
        pages[title] = text_el.text
    return pages


def import_players(wikitext: str) -> None:
    players = extract_players(wikitext)
    overview_sections: list[str] = []

    intro_md, _ = wikitext_to_markdown(
        re.split(r"== Эпоха", wikitext)[0] if "== Эпоха" in wikitext else wikitext
    )

    for name, (era, body, params) in players.items():
        rel = PLAYER_FILES.get(name, f"players/{name}")
        TITLE_TO_PATH[name] = rel
        frontmatter: dict = {
            "title": params.get("имя") or params.get("никнейм", name),
            "type": "игрок",
            "tags": ["player", "lore"],
        }
        mapping = {
            "никнейм": "nickname",
            "статус": "status",
            "роль": "role",
            "первое_появление": "first_seen",
            "группировка": "faction",
            "изображение": "skin",
        }
        for ru, en in mapping.items():
            if params.get(ru):
                frontmatter[en] = params[ru]
        if era:
            frontmatter["era"] = era
        write_note(rel, body, frontmatter)
        overview_sections.append(
            f"- [[{rel}|{name}]] — {params.get('роль', params.get('статус', ''))}"
        )

    overview = intro_md + "\n## Список игроков\n\n" + "\n".join(overview_sections) + "\n"
    write_note(
        "players/index",
        overview,
        {
            "title": "База данных игроков Semicraft",
            "tags": ["players", "lore"],
        },
    )


def main() -> int:
    if not XML_PATH.exists():
        print(f"Missing export file: {XML_PATH}", file=sys.stderr)
        return 1

    pages = parse_pages()
    clear_old_content()

    if "Игроки" in pages:
        import_players(pages.pop("Игроки"))

    for title, wikitext in pages.items():
        rel = TITLE_TO_PATH.get(title)
        if not rel:
            rel = slug_for_title(title)
        md, meta = wikitext_to_markdown(wikitext)
        frontmatter: dict = {}
        if title == "Заглавная страница":
            frontmatter = {
                "title": "Semicraft",
                "tags": ["home"],
                "aliases": ["Заглавная страница"],
            }
        elif title == "Заглавная страница/en":
            frontmatter = {"title": "Semicraft", "tags": ["home", "en"], "lang": "en"}
        elif meta.get("entity_params"):
            frontmatter = build_entity_frontmatter(meta["entity_params"], meta.get("tags", []))
        else:
            if meta.get("draft"):
                frontmatter["draft"] = True
            if meta.get("tags"):
                frontmatter["tags"] = sorted(set(meta["tags"]))
        write_note(rel, md, frontmatter or None)

    print(f"Imported {len(pages) + 1} pages into {CONTENT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
