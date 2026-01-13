import re
import xml.etree.ElementTree as ET

from config import build_chapter_regex_str
from constants import MISSING_CLASS, MISSING_MARKER
from num_utils import cn2an_simple


def get_toc_source(bk):
    nav_id = None
    ncx_id = None

    for manifest_id, href, mime in bk.manifest_iter():
        href_lower = href.lower()
        if "nav.xhtml" in href_lower or "nav.html" in href_lower:
            nav_id = manifest_id
        elif href_lower.endswith(".ncx") or mime == "application/x-dtbncx+xml":
            ncx_id = manifest_id

    if nav_id:
        return nav_id, "nav"
    if ncx_id:
        return ncx_id, "ncx"
    return None, None


def extract_texts_from_xml(content):
    texts = []
    try:
        clean_content = re.sub(r' xmlns="[^"]+"', "", content, count=1)
        clean_content = re.sub(r' xmlns:[a-z]+="[^"]+"', "", clean_content)
        root = ET.fromstring(clean_content)
        for elem in root.iter():
            if elem.text and elem.text.strip():
                texts.append(elem.text.strip())
            if elem.tail and elem.tail.strip():
                texts.append(elem.tail.strip())
    except Exception:
        matches = re.findall(r">([^<]+)<", content)
        texts = [m.strip() for m in matches if m.strip()]
    return texts


def get_nav_texts(bk):
    file_id, toc_type = get_toc_source(bk)

    if not file_id:
        return []

    try:
        content = bk.readfile(file_id)
    except Exception:
        return []

    return extract_texts_from_xml(content)


def get_chapter_info_from_nav(bk, config):
    file_id, toc_type = get_toc_source(bk)
    if not file_id or toc_type != "nav":
        return None, None, {}

    content = bk.readfile(file_id)

    chap_regex_str = build_chapter_regex_str(config)

    try:
        chap_re = re.compile(chap_regex_str)
    except:
        return file_id, content, {}

    chapter_map = {}
    pattern = re.compile(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', re.IGNORECASE)

    for match in pattern.finditer(content):
        href = match.group(1)
        text = match.group(2).strip()
        cm = chap_re.search(text)
        if cm:
            try:
                c_num = cn2an_simple(cm.group(1))
                chapter_map[c_num] = href
            except:
                pass

    return file_id, content, chapter_map


def find_nearest_existing_href(missing_num, chapter_map, all_chapters):
    sorted_chapters = sorted(all_chapters)

    for c in sorted_chapters:
        if c > missing_num and c in chapter_map:
            return chapter_map[c]

    for c in reversed(sorted_chapters):
        if c < missing_num and c in chapter_map:
            return chapter_map[c]

    if chapter_map:
        return list(chapter_map.values())[0]

    return "#"


def insert_missing_chapters_to_nav(bk, config, missing_chapters):
    file_id, content, chapter_map = get_chapter_info_from_nav(bk, config)

    if not file_id:
        return 0, "未找到 nav.xhtml 文件"

    if not chapter_map:
        return 0, "无法解析现有章节信息"

    prefix = config["chap_prefix"]
    suffix = config["chap_suffix"]
    all_chapters = set(chapter_map.keys())

    inserted = 0
    new_content = content

    for missing_num in sorted(missing_chapters, reverse=True):
        target_href = find_nearest_existing_href(missing_num, chapter_map, all_chapters)

        missing_title = f"{MISSING_MARKER}{prefix}{missing_num}{suffix}"

        new_li = f'<li class="{MISSING_CLASS}"><a href="{target_href}">{missing_title}</a></li>'

        next_chapters = [c for c in sorted(all_chapters) if c > missing_num]
        if next_chapters:
            next_chap = min(next_chapters)
            next_href = chapter_map.get(next_chap, "")
            if next_href:
                pattern = re.compile(
                    rf'(<li[^>]*>\s*<a[^>]*href="{re.escape(next_href)}"[^>]*>[^<]*</a>\s*</li>)',
                    re.IGNORECASE | re.DOTALL,
                )
                match = pattern.search(new_content)
                if match:
                    new_content = (
                        new_content[: match.start()]
                        + new_li
                        + "\n"
                        + new_content[match.start() :]
                    )
                    inserted += 1
                    continue

        prev_chapters = [c for c in sorted(all_chapters) if c < missing_num]
        if prev_chapters:
            prev_chap = max(prev_chapters)
            prev_href = chapter_map.get(prev_chap, "")
            if prev_href:
                pattern = re.compile(
                    rf'(<li[^>]*>\s*<a[^>]*href="{re.escape(prev_href)}"[^>]*>[^<]*</a>\s*</li>)',
                    re.IGNORECASE | re.DOTALL,
                )
                match = pattern.search(new_content)
                if match:
                    new_content = (
                        new_content[: match.end()]
                        + "\n"
                        + new_li
                        + new_content[match.end() :]
                    )
                    inserted += 1
                    continue

    if inserted > 0:
        bk.writefile(file_id, new_content)

    return inserted, None


def remove_missing_placeholders(bk):
    file_id, toc_type = get_toc_source(bk)

    if not file_id or toc_type != "nav":
        return 0, "未找到 nav.xhtml 文件"

    content = bk.readfile(file_id)

    pattern = re.compile(
        rf'<li[^>]*class="[^"]*{MISSING_CLASS}[^"]*"[^>]*>.*?</li>\s*',
        re.IGNORECASE | re.DOTALL,
    )

    new_content, count = pattern.subn("", content)

    if count == 0:
        pattern2 = re.compile(
            rf"<li[^>]*>\s*<a[^>]*>[^<]*{re.escape(MISSING_MARKER)}[^<]*</a>\s*</li>\s*",
            re.IGNORECASE | re.DOTALL,
        )
        new_content, count = pattern2.subn("", content)

    if count > 0:
        bk.writefile(file_id, new_content)

    return count, None
