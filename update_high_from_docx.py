# -*- coding: utf-8 -*-
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

HTML = Path("preview.html")
FAQ_XLSX = Path("Актуальное FAQ и Техническая помощь ученикам.xlsx")
STYLE_DOCX = Path("Стиль_оформления_заметок_по_модулям.docx")
HIGH_VIDEO_LESSONS_TXT = Path("Видеоуроки/Новый текстовый документ.txt")

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

COURSES = {
    "middle": {
        "docx": "Сообщение в чат в конце урока Middle Online.docx",
        "prefix": "Модуль Middle ",
        "const": "middleModulesData",
        "order": [
            ("Scratch", "Scratch"),
            ("Minecraft", "Minecraft"),
            ("Stencyl", "Stencyl"),
            ("App Inventor", "App Inventor"),
            ("Godot", "Godot"),
            ("JavaScript", "JavaScript"),
            ("Blender", "Blender"),
            ("Unity", "Unity"),
            ("HTML, CSS, JavaScript", "HTML, CSS, JavaScript"),
            ("Python", "Python"),
        ],
    },
    "high": {
        "docx": "Сообщение в чат в конце урока High Online.docx",
        "prefix": "Модуль High ",
        "const": "highModulesData",
        "order": [
            ("Scratch", "Scratch"),
            ("App Inventor", "App Inventor"),
            ("Stencyl", "Stencyl"),
            ("Godot", "Godot"),
            ("JavaScript", "JavaScript"),
            ("Unity", "Unity"),
            ("Blender", "Blender"),
            ("Unreal Engine", "Unreal Engine"),
            ("HTML, CSS, JavaScript", "HTML, CSS, JavaScript"),
            ("Python", "Python"),
            ("Android - Java", "Java - Android"),
        ],
    },
}

PROJECT_LABEL_MODULES = {
    "App Inventor": (7, 2),
    "Stencyl": (7, 2),
    "Godot": (7, 2),
    "Blender": (8, 2),
    "Unreal Engine": (11, 2),
}


def note_link(label, url):
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer" title="{url}">{label}</a>'


def problem_note(problem, solution, kind="Проблема", module_name=None):
    summary = styled_issue_summary(module_name, problem) if module_name else escape_html(problem)
    return (
        f'<details class="module-problem"><summary>{summary}</summary>'
        f'<div class="module-solution"><b>Решение:</b> {solution}</div></details>'
    )


def escape_html(value):
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def display_url_label(url):
    if "docs.google.com" in url:
        return "документ Google"
    if "drive.google.com" in url:
        return "Google Drive"
    if "disk.yandex.ru" in url:
        return "Яндекс Диск"
    return "ссылка"


def format_note_text(text):
    text = str(text or "")
    url_re = re.compile(r"(https?://[^\s<>'\"]+|www\.[^\s<>'\"]+)")
    result = []
    last = 0
    for match in url_re.finditer(text):
        result.append(escape_html(text[last : match.start()]))
        url = match.group(0)
        href = "https://" + url if url.lower().startswith("www.") else url
        result.append(note_link(display_url_label(href), href))
        last = match.end()
    result.append(escape_html(text[last:]))
    return "".join(result).replace("\n", "<br>")


def normalize_title(value):
    value = re.sub(r"<[^>]+>", " ", str(value or "").lower())
    value = value.replace("ё", "е")
    value = re.sub(r"[^\w\s]+", " ", value, flags=re.U)
    return re.sub(r"\s+", " ", value).strip()


STYLE_MODULE_ALIASES = {
    "Godot": "Game",
    "JavaScript": "Visual Studio Code",
    "HTML, CSS, JavaScript": "Visual Studio Code",
    "Java - Android": "IntelliJ IDEA",
}

STYLE_TITLE_ALIASES = {
    ("Scratch", normalize_title("В Desktop версии даже не двигается спрайт, дублируются скрипты")): "Не двигается спрайт в Desktop-версии Scratch (дублируются скрипты)",
    ("App Inventor", normalize_title("не открывается сайт App Inventor")): "Не открывается сайт App Inventor",
    ("App Inventor", normalize_title("ребенок не создал Google аккаунт")): "Ребёнок не создал Google-аккаунт",
    ("App Inventor", normalize_title("не получается тестировать на телефоне, процесс зависает на 40%")): "Зависает на 40% при тестировании на телефоне",
    ("Stencyl", normalize_title("Ошибка в Stencyl при попытке запустить игру/заготовку Не открывается Stencyl Forge/не загружаются актёры")): "Не запускается игра или заготовка Stencyl (Forge не открывается / не загружаются актёры)",
    ("Stencyl", normalize_title("Проблема с интерфейсом: сбились окна")): "Сбились окна интерфейса",
    ("Stencyl", normalize_title("Ошибка при установке Error opening file for writing: C:\\Program Files\\Stencylruntimes\\jre-win64\\bin\\awt.dll Click Abort to stop the installation, Retry to try again, or Ignore to skip this file.")): "Ошибка при установке Stencyl",
    ("Stencyl", normalize_title('Поведение "Camera follow" не работает, не следит за героем')): "Не работает Camera Follow",
    ("Stencyl", normalize_title("Невозможно открыть настройки в приложении, чтобы сменить язык.")): "Не открываются настройки языка",
    ("Stencyl", normalize_title("Главный актер перестал взаимодействовать с предметами, то есть все скрипты правильные, все настроено тоже идеально, но он просто насквозь проходит, будто их нет.")): "Главный актёр проходит сквозь предметы",
    ("Stencyl", normalize_title("Не работает Stencyl Forge.")): "Не работает Stencyl Forge",
    ("Stencyl", normalize_title("Ошибка с OGG файлами. Перебрасывает на музыку.")): "Ошибка с OGG-файлами",
    ("Godot", normalize_title("проект вылетает, лагает или вообще не открывается")): "Проект вылетает или не открывается",
    ("Godot", normalize_title("При запуске игры не виден персонажи и объекты")): "Не отображаются персонажи и объекты",
    ("Unity", normalize_title("не открывается сайт Unity, но установлен Unity Hub")): "Не открывается сайт Unity",
    ("Unity", normalize_title('Can’t add script component “***” because the script class cannot be found')): "Can't add script component because the script class cannot be found",
    ("Unity", normalize_title("временная папка переполнена или нет доступа к ней")): "Переполнена временная папка",
    ("Unity", normalize_title("пропали элементы интерфейса или сцена стала 2D")): "Пропали элементы интерфейса / сцена стала 2D",
    ("Blender", normalize_title("При запуске вылетает блендер без ошибок")): "Вылетает при запуске Blender",
    ("Blender", normalize_title("При просмотре с некоторой дистанции и исчезают объекты. Если камера отдаляется, то  исчезают объекты, как будто бы у камеры есть дальность прорисовки.")): "Исчезают объекты при отдалении камеры",
    ("Blender", normalize_title("Слабый компьютер, который не выдерживает работу версии")): "Компьютер не тянет Blender",
    ("Blender", normalize_title("На макбуке в блендере прокрутка колеса мыши не приближает объект.")): "На MacBook не работает приближение колесом",
    ("Blender", normalize_title("Исчезли окна outliner + properties")): "Пропали Outliner и Properties",
    ("Unreal Engine", normalize_title("Не получается скачать Unreal Engine через Epic Games Launcher")): "Не получается скачать Unreal Engine",
    ("Unreal Engine", normalize_title("Как открыть готовый проект (или заготовку) из загрузок в Unreal Engine")): "Как открыть готовый проект",
    ("Unreal Engine", normalize_title("Particles and Wind Control System не получается скачать и установить")): "Не устанавливается Particles and Wind Control System",
    ("Unreal Engine", normalize_title("Персонаж появляется в воздухе при запуске теста")): "Персонаж появляется в воздухе при запуске теста",
    ("Python", normalize_title("Проблема с установкой модуля pygame")): "Не устанавливается модуль pygame",
}


def styled_text_from_runs(runs):
    parts = ['<span class="issue-title">']
    for item in runs:
        text = item["text"]
        if not text:
            continue
        css_class = "issue-main" if item["bold"] else "issue-context"
        parts.append(f'<span class="{css_class}">{escape_html(text)}</span>')
    parts.append("</span>")
    return "".join(parts)


def read_style_docx():
    if not STYLE_DOCX.exists():
        return {}

    result = {}
    current_module = None
    current_section = None
    section_names = {"Важно", "Частые проблемы"}

    with zipfile.ZipFile(STYLE_DOCX) as docx:
        root = ET.fromstring(docx.read("word/document.xml"))

    for paragraph in root.findall(".//w:p", NS):
        runs = []
        for run in paragraph.findall("w:r", NS):
            text = "".join(node.text or "" for node in run.findall(".//w:t", NS))
            if not text:
                continue
            runs.append({"text": text, "bold": run.find("w:rPr/w:b", NS) is not None})

        full_text = "".join(item["text"] for item in runs).strip()
        if not full_text:
            continue
        if full_text in section_names:
            current_section = full_text
            continue
        if current_section is None or full_text in STYLE_MODULE_ALIASES.values() or full_text in {module for module in STYLE_MODULE_ALIASES} or full_text in {
            "Scratch",
            "App Inventor",
            "Stencyl",
            "Game",
            "Unity",
            "Blender",
            "Unreal Engine",
            "Python",
            "IntelliJ IDEA",
            "Visual Studio Code",
        }:
            current_module = full_text
            current_section = None
            continue
        if current_module and current_section == "Частые проблемы" and full_text != "—":
            result[(current_module, normalize_title(full_text))] = styled_text_from_runs(runs)

    return result


STYLE_SUMMARY_HTML = read_style_docx()


def styled_issue_summary(module_name, problem):
    plain_problem = re.sub(r"<[^>]+>", " ", str(problem or ""))
    normalized = normalize_title(plain_problem)
    style_module = STYLE_MODULE_ALIASES.get(module_name, module_name)
    target_title = STYLE_TITLE_ALIASES.get((module_name, normalized))
    target_key = normalize_title(target_title) if target_title else normalized
    return STYLE_SUMMARY_HTML.get((style_module, target_key), escape_html(plain_problem))


def install_note_from_body(body, index):
    text = body[index]["text"].strip()
    url = clean_url(body[index].get("url"))
    if not url:
        for next_paragraph in body[index + 1 : index + 4]:
            next_text = next_paragraph["text"].strip()
            next_url = clean_url(next_paragraph.get("url")) or clean_url(next_text)
            if next_url and "forms" not in next_url:
                url = next_url
                break

    if not url:
        return ""

    title = re.sub(r"https?://\S+", "", text).strip().rstrip(":")
    if not title:
        title = "Инструкция по установке"
    return f"{title}: {note_link(display_url_label(url), url)}"


def find_install_notes_for_next_module(previous_source):
    if not previous_source:
        return []

    for lesson in reversed(previous_source["lessons"]):
        body = lesson["body"]
        for index, paragraph in enumerate(body):
            if "инструкция по установ" not in paragraph["text"].strip().lower():
                continue
            note = install_note_from_body(body, index)
            if note:
                return [note]

    return []


INSTALL_SEARCH_TERMS = {
    "JavaScript": ["visual studio code", "vs code"],
    "HTML, CSS, JavaScript": ["visual studio code", "vs code"],
    "Blender": ["blender"],
    "Unreal Engine": ["unreal engine"],
    "Python": ["python"],
    "Java - Android": ["intellij idea", "intellij"],
}


def find_install_notes_by_terms(module_by_title, display_title):
    terms = INSTALL_SEARCH_TERMS.get(display_title, [])
    if not terms:
        return []

    for source in module_by_title.values():
        for lesson in source["lessons"]:
            body = lesson["body"]
            for index, paragraph in enumerate(body):
                text = paragraph["text"].strip()
                lower = text.lower()
                if "инструкция по установ" not in lower:
                    continue
                if not any(term in lower for term in terms):
                    continue
                note = install_note_from_body(body, index)
                if note:
                    return [note]

    return []


def video_module_name(line):
    lower = line.lower().strip(" :")
    if "scratch" in lower:
        return "Scratch"
    if "app" in lower and "inventor" in lower:
        return "App Inventor"
    if "stencyl" in lower:
        return "Stencyl"
    if "godot" in lower:
        return "Godot"
    if "javascript" in lower:
        return "JavaScript"
    if "unity" in lower:
        return "Unity"
    if "blender" in lower:
        return "Blender"
    return ""


def read_high_lesson_videos():
    if not HIGH_VIDEO_LESSONS_TXT.exists():
        return {}

    raw = HIGH_VIDEO_LESSONS_TXT.read_bytes()
    text = ""
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "utf-16"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        return {}

    entries = {}
    current_module = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = re.match(r"^(\d+)\s*(?:[-–—])?\s*(.*)$", line)
        if not match:
            module_name = video_module_name(line)
            if module_name:
                current_module = module_name
            continue

        overall_number = int(match.group(1))
        value = match.group(2).strip()
        url_match = re.search(r"https?://\S+", value)
        entries[overall_number] = {
            "module": current_module,
            "url": clean_url(url_match.group(0)) if url_match else "",
            "raw": value,
        }

    return entries


def column_name(cell_ref):
    return re.sub(r"\d+", "", cell_ref or "")


def read_faq_workbook():
    if not FAQ_XLSX.exists():
        return {}

    ns_sheet = {
        "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    ns_rels = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with zipfile.ZipFile(FAQ_XLSX) as workbook:
        shared_strings = []
        try:
            root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", ns_sheet):
                shared_strings.append("".join(node.text or "" for node in item.findall(".//a:t", ns_sheet)))
        except KeyError:
            pass

        workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
        rels_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        workbook_rels = {node.attrib["Id"]: node.attrib["Target"] for node in rels_root}
        sheets = {}

        for sheet in workbook_root.findall(".//a:sheet", ns_sheet):
            name = sheet.attrib.get("name", "")
            rel_id = sheet.attrib.get("{%s}id" % ns_sheet["r"])
            target = workbook_rels.get(rel_id, "")
            if not target:
                continue
            sheet_path = "xl/" + target.lstrip("/").replace("../", "")
            sheet_root = ET.fromstring(workbook.read(sheet_path))

            sheet_rel_path = "xl/worksheets/_rels/" + Path(sheet_path).name + ".rels"
            sheet_rels = {}
            try:
                sheet_rels_root = ET.fromstring(workbook.read(sheet_rel_path))
                sheet_rels = {node.attrib["Id"]: node.attrib.get("Target", "") for node in sheet_rels_root}
            except KeyError:
                pass

            hyperlinks = {}
            for link in sheet_root.findall(".//a:hyperlink", ns_sheet):
                ref = link.attrib.get("ref", "")
                link_rel_id = link.attrib.get("{%s}id" % ns_sheet["r"])
                if ref and link_rel_id in sheet_rels:
                    hyperlinks[ref] = sheet_rels[link_rel_id]

            def cell_value(cell):
                cell_type = cell.attrib.get("t")
                value = cell.find("a:v", ns_sheet)
                raw = value.text if value is not None else ""
                if cell_type == "s" and raw:
                    return shared_strings[int(raw)]
                if cell_type == "inlineStr":
                    return "".join(node.text or "" for node in cell.findall(".//a:t", ns_sheet))
                return raw

            rows = []
            for row in sheet_root.findall(".//a:sheetData/a:row", ns_sheet):
                row_data = {}
                for cell in row.findall("a:c", ns_sheet):
                    ref = cell.attrib.get("r", "")
                    row_data[column_name(ref)] = {
                        "text": cell_value(cell).strip(),
                        "url": clean_url(hyperlinks.get(ref, "")),
                    }
                rows.append(row_data)
            sheets[name] = rows

    return sheets


def faq_solution_html(solution, material):
    parts = [format_note_text(solution)]
    material_text = material.get("text", "").strip()
    material_url = clean_url(material.get("url", ""))
    if material_text or material_url:
        if material_url:
            label = material_link_label(material_text, material_url)
            parts.append("<br><br>" + note_link(escape_html(label), material_url))
        elif re.search(r"https?://|www\.", material_text):
            parts.append("<br><br>" + format_note_text(material_text))
    return "".join(parts)


def material_link_label(text, url):
    cleaned = re.sub(r"https?://\S+", "", text or "")
    lines = [line.strip(" .:") for line in cleaned.splitlines() if line.strip(" .:")]
    joined = " ".join(lines)
    lower = joined.lower()
    if "видеоролик" in lower:
        return "Видеоролик"
    if "инструкция" in lower:
        return "Инструкция"
    if "установ" in lower and "mac" in lower:
        return "Установщик"
    if not joined or "ссылка" in lower or len(joined) > 70:
        return display_url_label(url)
    return joined


FAQ_SKIP_ALL = {"App Inventor"}

FAQ_SKIP_TITLES = {
    "Scratch": [
        "Не прогружается сайт Scratch.Дублируется код блоков у одного спрайта в другого.",
        "Не прогружается сайт Scratch Jr или работает нестабильно: исчезают блоки, спрайты.",
    ],
    "Stencyl": [
        "Unexpected Problem",
        "Ouch, this should not have happened",
    ],
    "Godot": [
        "Бесконечная прогрузка при создании или загрузки проекта.",
    ],
    "Unity": [
        "При установке не получается зайти в аккаунт. Не прогружается юнити хаб",
        "Не открывается проект/не загружается повторно новый проект в юнити хабе.",
    ],
}


def should_skip_faq_note(module_name, title, solution, material):
    if module_name in FAQ_SKIP_ALL:
        return True

    normalized_title = normalize_title(title)
    for skipped in FAQ_SKIP_TITLES.get(module_name, []):
        if normalize_title(skipped) in normalized_title:
            return True

    combined = "\n".join(
        [
            title or "",
            solution or "",
            material.get("text", "") if material else "",
            material.get("url", "") if material else "",
        ]
    ).lower()
    if "vpn://" in combined or "впн" in combined:
        return True

    return False


def build_faq_notes_for_module(module_name):
    rows = FAQ_DATA.get(module_name, [])
    notes = []
    seen = set()
    for row in rows[3:]:
        entries = [
            ("Проблема", row.get("A", {}), row.get("B", {}), row.get("C", {})),
            ("Проблема", row.get("D", {}), row.get("E", {}), row.get("F", {})),
        ]
        for kind, title_cell, solution_cell, material_cell in entries:
            title = title_cell.get("text", "").strip()
            solution = solution_cell.get("text", "").strip()
            if not title or not solution:
                continue
            if should_skip_faq_note(module_name, title, solution, material_cell):
                continue
            normalized = normalize_title(title)
            if normalized in seen:
                continue
            seen.add(normalized)
            notes.append(problem_note(title, faq_solution_html(solution, material_cell), kind, module_name=module_name))
    return notes


SCRATCH_MODULE_NOTES = [
    "рабочая онлайн версия " + note_link("Scratch Kulibin", "https://scratch.kulibin.app/"),
    "оффлайн установщик Google Drive: "
    + note_link(
        "Google Drive",
        "https://drive.google.com/file/d/1DvajylAwXvTHrVB3yX3UANMGTX6HzOY6/view?usp=sharing",
    ),
    "настроить ребятам контурТолк чтобы все были с приложения:<br>"
    + note_link("скачать КонтурТолк", "https://app.ktalk.ru/download/app?utm_referer=94nb0gbg.ktalk.ru"),
    problem_note(
        "В Desktop версии даже не двигается спрайт, дублируются скрипты",
        "1 метод. Отправляете ученику свой файл с заготовкой. Поломка именно в нем.<br>"
        "2 метод. Зайдите в спрайта и переключите костюм, скрипты должны обновиться.",
        module_name="Scratch",
    ),
]

MIDDLE_MINECRAFT_MODULE_NOTES = [
    "Инструкция по установке Minecraft: "
    + note_link(
        "документ Google",
        "https://docs.google.com/document/d/1jgaWpiQdHQH38lLtdP5pd6yE78hqbFC5/edit?usp=sharing&ouid=101384562489296174291&rtpof=true&sd=true",
    ),
    "<b>Пушить в чат через день чтобы установили по инструкции! Иначе вся группа придет без майнкрафта!</b>",
]

MIDDLE_STENCYL_MODULE_NOTES = [
    "<b>Не давать заготовки из ЕРП! Они не работают!</b>",
    "Заготовка для дз у мидлов: "
    + note_link("папка Google Drive", "https://drive.google.com/drive/folders/10UX1vbgbc1gFdEGzxobhyxC-oSDCpJgZ"),
]

HIGH_STENCYL_MODULE_NOTES = [
    "<b>Не давать заготовки из ЕРП! Они не работают!</b>",
    "Заготовки для ДЗ у хаев (Game): "
    + note_link("папка Google Drive", "https://drive.google.com/drive/folders/1QRz-jb2nUKIWdJlXPxzGanrpb6VcLQXR"),
]

MIDDLE_STENCYL_STARTERS = {
    1: "https://drive.google.com/file/d/1CQAcbpHcZjB6dAr6Z08NRTgUnT98Gim5/view?usp=drive_link",
}

HIGH_STENCYL_STARTERS = {
    1: "https://drive.google.com/file/d/18bHR-DaZ42HwbjKDCU6xiB1z3nNYk7IH/view?usp=drive_link",
    2: "https://drive.google.com/file/d/1z2gqCGTrwOBDzAmmLiVVzPoX0YRPMqCU/view?usp=drive_link",
    3: "https://drive.google.com/file/d/1Bi4fkoEwqk5CWzcZyhWnvP03_1aMbDV2/view?usp=drive_link",
    4: "https://drive.google.com/file/d/1AiTZuoliAEgBSXvSjdXizTRjVFJG2-Xn/view?usp=drive_link",
    5: "https://drive.google.com/file/d/12Pr6MdEqP5JGER6IyG0L0Tncu4KvMAxS/view?usp=drive_link",
}

APP_INVENTOR_MODULE_NOTES = [
    "Инструкция по установке: "
    + note_link(
        "документ Google",
        "https://docs.google.com/document/d/172oKcMRGu_PFjh9FoHHONhqhowStbfqQlxrWLovPGAw/edit?usp=sharing",
    ),
    problem_note(
        "не открывается сайт App Inventor",
        "устанавливаем оффлайн версию: "
        + note_link("Google Drive", "https://drive.google.com/file/d/152gyZ_eW8v8Ar0mQaBds16OAz9Bn6vX5/view")
        + " или "
        + note_link("Яндекс Диск", "https://disk.yandex.ru/d/JiuvQe2IuI-svA")
        + ". Инструкция по работе с оффлайн версией: "
        + note_link(
            "документ Google",
            "https://docs.google.com/document/d/1VTT4DibkpNFWKWNC69Edq4tz3YlCbdPMFqAPKCgghwk/edit?tab=t.0",
        ),
        module_name="App Inventor",
    ),
    problem_note(
        "ребенок не создал Google аккаунт",
        "можно зайти без него. Важно сохранить код, который даст App Inventor: "
        + note_link("code.appinventor.mit.edu", "https://code.appinventor.mit.edu/"),
        module_name="App Inventor",
    ),
    problem_note(
        "не получается тестировать на телефоне, процесс зависает на 40%",
        "<ol><li>проверить, что телефон и компьютер в одной Wi-Fi сети;</li><li>сменить браузер;</li><li>попросить выключить ДискордЗапрет, если он установлен;</li><li>установить BlueStacks для тестирования.</li></ol>",
        module_name="App Inventor",
    ),
]

GODOT_COMPATIBILITY_SOLUTION = (
    "открываем проект и в верхнем правом углу ищем Forward+ зеленым цветом. Нажимаем и меняем на Compatibility. "
    "Если такой надписи нет: Project → Project Settings → General → Rendering → Renderer → Rendering Method.<br><br>"
    "Или до запуска проекта: в менеджере проектов нажать ПКМ по проекту → Посмотреть в проводнике → открыть project.godot через Блокнот или Notepad++ → найти строку "
    '<code>config/features=PackedStringArray("4.6", "Forward Plus")</code> и заменить на '
    '<code>config/features=PackedStringArray("4.6", "Compatibility")</code>.'
)

GODOT_MODULE_NOTES = [
    problem_note("проект вылетает, лагает или вообще не открывается", GODOT_COMPATIBILITY_SOLUTION, module_name="Godot"),
]

UNITY_MODULE_NOTES = [
    "Инструкция по установке Unity: "
    + note_link(
        "документ Google",
        "https://docs.google.com/document/d/1dQnyILlvvie9BLVEXF1ZU3X6sPO7x2uolAqz4tRNnfU/edit?tab=t.0",
    ),
    "<b>Проверить что установлена нужная версия: 2019.4.3f1, а не 2019.4.30f1 - это разные версии!!</b>",
    problem_note(
        "не открывается сайт Unity, но установлен Unity Hub",
        "дать прямую ссылку: " + note_link("unityhub://2019.4.3f1/f880dceab6fe", "unityhub://2019.4.3f1/f880dceab6fe"),
        module_name="Unity",
    ),
    problem_note(
        "не работает донаборщик у детей",
        "проверяем, чтобы был установлен Visual Studio и настроен: Edit → Preferences → External Tools → External Script Editor → выбрать VS Studio, сохранить и запустить ее. Может попросить установить C# модуль - устанавливаем.",
        module_name="Unity",
    ),
    problem_note(
        'Can’t add script component “***” because the script class cannot be found',
        "проблема в названии класса последнего скрипта или ошибка в другом скрипте проекта.<ol><li>Проверьте, совпадает ли строка <code>public class</code> с названием файла скрипта.</li><li>Если совпадает, откройте Console, нажмите Clear и посмотрите актуальные ошибки.</li><li>Очистите все скрипты от ошибок. Если сложно найти ошибку, прогоните скрипт через DeepSeek с промптом: <b>Исправь ошибки, не добавляй комментарии и ничего лишнего в код. Скрипт: *тут скрипт ребенка*</b></li></ol>",
        module_name="Unity",
    ),
    problem_note(
        "временная папка переполнена или нет доступа к ней",
        "проверить наличие папки <code>C:\\windows\\installer</code>. Если ее нет, создать заново. Затем сохранить и перезапустить проект.",
        module_name="Unity",
    ),
    problem_note(
        "пропали элементы интерфейса или сцена стала 2D",
        "Window → Layouts → Revert Factory Settings. Или Window → Layouts → Reset to Default Layout.",
        module_name="Unity",
    ),
]


def clean_url(url):
    url = (url or "").strip().replace(" ", "")
    if not url:
        return ""
    url = url.replace("?usp=sharingAi", "?usp=sharing")
    url = url.replace("&usp=sharingAi", "&usp=sharing")
    if url.startswith("docs.google.com") or url.startswith("drive.google.com"):
        url = "https://" + url
    return url


HIGH_LESSON_VIDEOS = read_high_lesson_videos()
HIGH_VIDEO_MISMATCHES = []


FAQ_DATA = read_faq_workbook()


def read_paragraphs(docx_path):
    docx = zipfile.ZipFile(docx_path)
    relroot = ET.fromstring(docx.read("word/_rels/document.xml.rels"))
    rels = {node.attrib.get("Id"): node.attrib.get("Target") for node in relroot}
    root = ET.fromstring(docx.read("word/document.xml"))

    def para_info(paragraph):
        text = []
        urls = []

        def walk(node, current_url=None):
            tag = node.tag.split("}")[-1]
            if tag == "hyperlink":
                rid = node.attrib.get("{%s}id" % NS["r"])
                current_url = rels.get(rid) or current_url
            if tag == "t":
                text.append(node.text or "")
            for child in node:
                walk(child, current_url)
            if tag == "hyperlink" and current_url:
                urls.append(current_url)

        walk(paragraph)
        return "".join(text).strip(), clean_url(urls[0] if urls else "")

    paragraphs = []
    for paragraph in root.findall(".//w:body//w:p", NS):
        text, url = para_info(paragraph)
        if text:
            paragraphs.append({"text": text, "url": url})
    return paragraphs


def split_modules(paragraphs, prefix):
    lesson_re = re.compile(r"^([0-9]+) +урок\.", re.I)
    modules = []
    current_module = None
    current_lesson = None

    for paragraph in paragraphs:
        text = paragraph["text"]
        if text.startswith(prefix):
            current_module = {"title": text.replace(prefix, "").strip(), "lessons": []}
            modules.append(current_module)
            current_lesson = None
            continue

        if not current_module:
            continue

        if lesson_re.match(text):
            if (
                current_module["lessons"]
                and current_module["lessons"][-1]["heading"] == text
                and not current_module["lessons"][-1]["body"]
            ):
                continue
            current_lesson = {"heading": text, "body": []}
            current_module["lessons"].append(current_lesson)
            continue

        if current_lesson:
            current_lesson["body"].append(paragraph)

    return {module["title"]: module for module in modules}


def module_label(display_title, count):
    if display_title in PROJECT_LABEL_MODULES:
        base, projects = PROJECT_LABEL_MODULES[display_title]
        if count == base + projects:
            return f"{base} занятий + {projects} проектных"
    return f"{count} занятий"


def format_parent_text(text):
    target = "Все ребята молодцы, отлично справились с заданиями!"
    lines = text.split("\n")
    formatted = []
    for line in lines:
        if line.strip() == target:
            if formatted and formatted[-1] != "":
                formatted.append("")
            formatted.append(target)
            formatted.append("")
        else:
            formatted.append(line)
    return "\n".join(formatted).strip()


def split_parent_messages(text):
    marker = "Вторым сообщением:"
    if marker not in text:
        return text, ""
    first, second = text.split(marker, 1)
    return format_parent_text(first.strip()), format_parent_text(second.strip())


def second_message_topic(text):
    lower = text.lower()
    if "нейросет" in lower:
        return "нейросети"
    if "английск" in lower or "english" in lower:
        return "английский"
    return "дополнительный урок"


def extract_lesson(display_title, lesson, project_lessons=False, course_const=""):
    body = lesson["body"]
    starter = ""
    project = ""
    test = ""
    lesson_video = ""
    message = []
    index = 0

    while index < len(body):
        text = body[index]["text"].strip()
        url = clean_url(body[index].get("url"))
        label = None
        rest = ""

        for candidate in ("Заготовка", "Готовый проект", "Тест"):
            if text == candidate or text.startswith(candidate):
                label = candidate
                rest = text[len(candidate) :].strip()
                break

        if label:
            value = url
            if not value and index + 1 < len(body):
                next_text = body[index + 1]["text"].strip()
                next_url = clean_url(body[index + 1].get("url"))
                if next_url or next_text.startswith(
                    ("http://", "https://", "docs.google.com", "drive.google.com")
                ):
                    value = next_url or clean_url(next_text)
                    index += 1
            if label == "Заготовка":
                starter = value
            elif label == "Готовый проект":
                project = value
            else:
                test = value
            if rest:
                message.append(rest)
        elif text.startswith(("http://", "https://", "docs.google.com", "drive.google.com")):
            pass
        else:
            message.append(text)

        index += 1

    number = int(re.match(r"^([0-9]+)", lesson["heading"]).group(1))
    name = f"Урок {number}"
    label = f"занятие {number}"
    if project_lessons and display_title in PROJECT_LABEL_MODULES:
        base, _ = PROJECT_LABEL_MODULES[display_title]
        if number > base:
            project_number = number - base
            name = f"Проектное занятие {project_number}"
            label = f"проект по модулю {display_title}"

    if course_const == "middleModulesData" and display_title == "Stencyl":
        starter = MIDDLE_STENCYL_STARTERS.get(number, starter)
    if course_const == "highModulesData" and display_title == "Stencyl":
        starter = HIGH_STENCYL_STARTERS.get(number, starter)

    problems = []
    if display_title == "Scratch" and number == 6:
        problems.extend(
            [
                "<b>Проблема: у ребят может не отображаться арбуз.</b><br><b>Решение:</b> удалить арбуз и добавить заново из стандартного списка спрайтов.",
                "<b>Проблема: стол может выходить вперед и перекрывать другие предметы.</b><br><b>Решение:</b> либо удалить стол, либо для стола добавить блок «перейти на задний слой» из блоков внешнего вида. Для остальных предметов добавить блок «перейти на передний план». Блоки можно просто добавить и нажать на них, соединять с основной командой не нужно.",
            ]
        )
    if display_title == "Godot" and number == 1:
        problems.append(
            "<b>Проблема: проект вылетает, лагает или вообще не открывается.</b><br><b>Решение:</b> "
            + GODOT_COMPATIBILITY_SOLUTION
        )
    if display_title == "App Inventor" and number == 6:
        problems.append(
            "<b>Проблема: не работает распознавание на iPhone.</b><br><b>Решение:</b> "
            "добавить блок строчные буквы для получения результата в блок "
            "«Когда РаспознавательРечи1.ПослеПолученияТекста» в первый блок «Если»."
        )

    parent_text, second_parent_text = split_parent_messages(format_parent_text("\n".join(message).strip()))
    next_special_lesson = second_message_topic(second_parent_text) if second_parent_text else ""
    if "Roblox" in parent_text or "Roblox Studio" in parent_text:
        prefix = parent_text.split("А уже на следующем уроке")[0].rstrip()
        parent_text = (
            prefix
            + "\nА уже на следующем уроке у нас начнётся новый модуль - Godot!\n"
            + "Мы будем работать в Godot - это игровой движок, в котором можно создавать 2D и 3D-игры. "
            + "На модуле познакомимся с интерфейсом, сценами, узлами и скриптами.\n"
            + "На следующем уроке мы:\n"
            + "- познакомимся с игровым движком Godot;\n"
            + "- изучим интерфейс программы;\n"
            + "- создадим персонажа и добавим ему скрипт;\n"
            + "- научим персонажа двигаться!"
        )

    return {
        "name": name,
        "label": label,
        "title": f"{display_title} - {name}{f' (следующий урок: {next_special_lesson}!)' if next_special_lesson else ''}",
        "subtitle": f"урок {number} модуля {display_title}",
        "metaType": "Урок",
        "links": {
            "starter": starter,
            "project": project,
            "lessonVideo": lesson_video,
            "video": test,
            "myquiz": "",
            "materials": "",
        },
        "parentText": parent_text,
        "secondParentText": second_parent_text,
        "nextSpecialLesson": next_special_lesson,
        "notes": [],
        "problems": problems,
        "extras": [],
    }


def note_summary(note):
    match = re.search(r"<summary>(.*?)</summary>", note, re.S)
    if match:
        text = re.sub(r"<[^>]+>", "", match.group(1))
        return re.sub(r"^(Проблема|Лайфхак):\s*", "", text).strip()
    text = re.sub(r"<[^>]+>", "", note)
    return text[:120].strip()


def extend_unique_notes(target, additions):
    existing_text = normalize_title(" ".join(re.sub(r"<[^>]+>", " ", note) for note in target))
    existing_titles = {normalize_title(note_summary(note)) for note in target}
    for note in additions:
        title = normalize_title(note_summary(note))
        if not title:
            continue
        if title in existing_titles or title in existing_text:
            continue
        target.append(note)
        existing_titles.add(title)
        existing_text += " " + title


def apply_high_lesson_videos(modules):
    overall_number = 1
    seen_numbers = set()
    for module in modules:
        for lesson in module["lessons"]:
            entry = HIGH_LESSON_VIDEOS.get(overall_number)
            if entry:
                seen_numbers.add(overall_number)
                expected_module = entry.get("module")
                if expected_module and expected_module != module["name"]:
                    HIGH_VIDEO_MISMATCHES.append(
                        {
                            "lesson": overall_number,
                            "txt_module": expected_module,
                            "site_module": module["name"],
                            "site_lesson": lesson["name"],
                        }
                    )
                if entry.get("url"):
                    lesson["links"]["lessonVideo"] = entry["url"]
            overall_number += 1

    for lesson_number, entry in sorted(HIGH_LESSON_VIDEOS.items()):
        if lesson_number not in seen_numbers and entry.get("url"):
            HIGH_VIDEO_MISMATCHES.append(
                {
                    "lesson": lesson_number,
                    "txt_module": entry.get("module") or "не указан",
                    "site_module": "нет такого занятия на сайте",
                    "site_lesson": "",
                }
            )


def build_modules(config):
    module_by_title = split_modules(read_paragraphs(config["docx"]), config["prefix"])
    built_modules = []

    for module_index, (source_title, display_title) in enumerate(config["order"]):
        source = module_by_title[source_title]
        lessons = []
        seen_numbers = set()
        has_project_lessons = module_label(display_title, len(source["lessons"])) != f'{len(source["lessons"])} занятий'
        for lesson in source["lessons"]:
            number = int(re.match(r"^([0-9]+)", lesson["heading"]).group(1))
            if number in seen_numbers:
                continue
            seen_numbers.add(number)
            lessons.append(extract_lesson(display_title, lesson, has_project_lessons, config["const"]))

        module_notes = []
        if display_title == "Scratch":
            module_notes.extend(SCRATCH_MODULE_NOTES)
        if config["const"] == "middleModulesData" and display_title == "Minecraft":
            module_notes.extend(MIDDLE_MINECRAFT_MODULE_NOTES)
        if config["const"] == "middleModulesData" and display_title == "Stencyl":
            module_notes.extend(MIDDLE_STENCYL_MODULE_NOTES)
        if config["const"] == "highModulesData" and display_title == "Stencyl":
            module_notes.extend(HIGH_STENCYL_MODULE_NOTES)
        if display_title == "App Inventor":
            module_notes.extend(APP_INVENTOR_MODULE_NOTES)
        if display_title == "Godot":
            module_notes.extend(GODOT_MODULE_NOTES)
        if display_title == "Unity":
            module_notes.extend(UNITY_MODULE_NOTES)
        if not module_notes and module_index > 0:
            previous_source_title = config["order"][module_index - 1][0]
            module_notes.extend(find_install_notes_for_next_module(module_by_title.get(previous_source_title)))
        if not module_notes:
            module_notes.extend(find_install_notes_by_terms(module_by_title, display_title))
        extend_unique_notes(module_notes, build_faq_notes_for_module(display_title))
        if display_title == "Godot":
            module_notes.append(
                "<b>Если дети слабые, сразу научить их пользоваться донаборщиком + показать как открывать сцены игроков и т.д. из главной сцены!</b>"
            )
        for lesson in lessons:
            if lesson.get("nextSpecialLesson"):
                lesson_number = re.search(r"\d+", lesson["name"])
                module_notes.append(
                    f"<b>После урока {lesson_number.group(0) if lesson_number else lesson['name']} будут {lesson['nextSpecialLesson']}, сообщить детям об этом.</b>"
                )

        built_modules.append(
            {
                "name": display_title,
                "label": module_label(display_title, len(lessons)),
                "note": module_notes,
                "lessons": lessons,
            }
        )

    if config["const"] == "highModulesData":
        apply_high_lesson_videos(built_modules)

    return built_modules


def replace_const(html, const_name, data):
    insert = (
        f"    const {const_name} = "
        + json.dumps(data, ensure_ascii=False, indent=6)
        + ";\n\n"
    )

    marker = f"    const {const_name} = "
    if marker in html:
        start = html.index(marker)
        end_candidates = []
        for candidate in ("    const middleModulesData = ", "    const highModulesData = ", "    const data = {"):
            pos = html.find(candidate, start + len(marker))
            if pos != -1:
                end_candidates.append(pos)
        end = min(end_candidates)
        return html[:start] + insert + html[end:]
    return html.replace("    const data = {", insert + "    const data = {", 1)


def update_html(course_data):
    html = HTML.read_text(encoding="utf-8")

    for config in COURSES.values():
        html = replace_const(html, config["const"], course_data[config["const"]])

    middle_old = """      middle: {
        title: "Middle",
        listTitle: "Модули курса",
        note: [
          "Модули Middle пока не расписаны.",
          "Когда появится список модулей, их можно добавить сюда без изменения дизайна."
        ],
        items: [
          emptyLesson("Модули пока не добавлены", "Пришли список модулей Middle, и они появятся в этом меню.")
        ]
      },"""
    middle_new = """      middle: {
        title: "Middle",
        listTitle: "Модули курса",
        note: [
          "Перед стартом модуля проверить заготовки, готовые проекты и тесты из документа.",
          "После урока отправлять родителям сообщение из блока «Сообщение после урока».",
          "Старый модуль заменён на Godot."
        ],
        items: middleModulesData
      },"""
    if middle_old in html:
        html = html.replace(middle_old, middle_new, 1)
    elif "items: middleModulesData" not in html:
        raise RuntimeError("Could not replace Middle data block")
    html = html.replace(
        "Roblox Studio пропущен; вместо него используется Godot.",
        "Старый модуль заменён на Godot.",
    )

    high_old = """        items: [
          module("Scratch", 6),
          module("App Inventor", 9, "7 занятий + 2 проектных"),
          module("Stencyl", 9, "7 занятий + 2 проектных"),
          module("Godot", 9, "7 занятий + 2 проектных"),
          module("JavaScript", 7),
          module("Unity", 17),
          module("Blender", 10, "8 занятий + 2 проектных"),
          module("Unreal Engine", 13, "11 занятий + 2 проектных"),
          module("HTML, CSS, JavaScript", 13),
          module("Python", 18),
          module("Java - Android", 9)
        ]"""
    if high_old in html:
        html = html.replace(high_old, "        items: highModulesData", 1)

    html = html.replace("—", "-")
    HTML.write_text(html, encoding="utf-8")


def main():
    course_data = {}
    if HIGH_LESSON_VIDEOS:
        video_url_count = sum(1 for item in HIGH_LESSON_VIDEOS.values() if item.get("url"))
        print(f"high lesson videos: {video_url_count} links, {len(HIGH_LESSON_VIDEOS)} numbered rows")
    for course_name, config in COURSES.items():
        modules = build_modules(config)
        course_data[config["const"]] = modules
        print(f"{course_name}: {len(modules)} modules")
        for module in modules:
            starters = sum(1 for lesson in module["lessons"] if lesson["links"]["starter"])
            projects = sum(1 for lesson in module["lessons"] if lesson["links"]["project"])
            tests = sum(1 for lesson in module["lessons"] if lesson["links"]["video"])
            print(
                f"  {module['name']}: {len(module['lessons'])} lessons, "
                f"starters {starters}, projects {projects}, tests {tests}"
            )
    if HIGH_VIDEO_MISMATCHES:
        print("high lesson video mismatches:")
        for item in HIGH_VIDEO_MISMATCHES:
            print(
                f"  lesson {item['lesson']}: txt {item['txt_module']} -> "
                f"site {item['site_module']} {item['site_lesson']}".strip()
            )
    update_html(course_data)


if __name__ == "__main__":
    main()
