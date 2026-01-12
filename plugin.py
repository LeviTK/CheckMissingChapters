import sys
import re
import os
import json
import xml.etree.ElementTree as ET
from pyqt_import import *

# --- Configuration ---
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "chap_prefix": "第",
    "chap_num_type": "mixed",  # mixed, arabic, cn_lower, cn_upper
    "chap_suffix": "章",
    "custom_suffixes": ["章", "回", "节", "话", "集"],
    "enable_volume": False,
    "vol_regex": r"第\s*([0-9]+|[零〇一二三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟萬两]+)\s*[卷部辑册幕篇]",
    "chap_reset_mode": "reset_1",
    "auto_detect_reset": False,
}

# 数字模式正则
NUM_PATTERNS = {
    "mixed": r"[0-9]+|[零〇一二三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟萬两]+",
    "arabic": r"[0-9]+",
    "cn_lower": r"[零〇一二三四五六七八九十百千万两]+",
    "cn_upper": r"[壹贰叁肆伍陆柒捌玖拾佰仟萬]+",
}

NUM_TYPE_NAMES = {
    "mixed": "混合模式",
    "arabic": "阿拉伯数字",
    "cn_lower": "中文小写",
    "cn_upper": "中文大写",
}


def load_or_create_config():
    """Load config from file, or create default if missing."""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                for k, v in user_config.items():
                    config[k] = v
        except Exception:
            pass
    else:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
    return config


def save_config(config):
    """Save config to file."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


# --- Utilities ---
def cn2an_simple(text):
    """
    Chinese numeral to Integer conversion.
    Supports: 0-99999999 (up to 亿-1)
    Examples: 十二->12, 一百二十三->123, 二千零五->2005, 一万二千三百四十五->12345
    """
    cn_nums = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "壹": 1,
        "二": 2,
        "贰": 2,
        "两": 2,
        "三": 3,
        "叁": 3,
        "四": 4,
        "肆": 4,
        "五": 5,
        "伍": 5,
        "六": 6,
        "陆": 6,
        "七": 7,
        "柒": 7,
        "八": 8,
        "捌": 8,
        "九": 9,
        "玖": 9,
    }
    cn_units = {
        "十": 10,
        "拾": 10,
        "百": 100,
        "佰": 100,
        "千": 1000,
        "仟": 1000,
        "万": 10000,
        "萬": 10000,
    }

    text = text.strip()
    if not text:
        return 0

    if text.isdigit():
        return int(text)

    if len(text) == 1 and text in cn_nums:
        return cn_nums[text]

    result = 0
    wan_part = 0
    current_section = 0
    current_num = 0

    i = 0
    while i < len(text):
        char = text[i]

        if char in cn_nums:
            current_num = cn_nums[char]
        elif char in cn_units:
            unit = cn_units[char]

            if unit == 10000:
                current_section += current_num
                wan_part = (wan_part + current_section) * 10000
                current_section = 0
                current_num = 0
            else:
                if (
                    current_num == 0
                    and unit == 10
                    and current_section == 0
                    and wan_part == 0
                ):
                    current_num = 1
                current_section += current_num * unit
                current_num = 0
        i += 1

    result = wan_part + current_section + current_num
    return result


def get_toc_source(bk):
    """
    Find TOC file: nav.xhtml (EPUB3) or toc.ncx (EPUB2).
    Returns: (file_id, toc_type) where toc_type is 'nav' or 'ncx', or (None, None)
    """
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
    """Extract all text content from XML/HTML content."""
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
    """Extract text content from nav.xhtml (EPUB3) or toc.ncx (EPUB2)."""
    file_id, toc_type = get_toc_source(bk)

    if not file_id:
        return []

    try:
        content = bk.readfile(file_id)
    except Exception:
        return []

    return extract_texts_from_xml(content)


def format_missing_chapters(missing, group_size=30):
    """
    格式化缺失章节列表，超过 group_size 时分组折叠显示。
    """
    if not missing:
        return ""

    total = len(missing)
    if total <= group_size:
        return ", ".join(str(x) for x in missing)

    lines = []
    for i in range(0, total, group_size):
        group = missing[i : i + group_size]
        group_start = i + 1
        group_end = min(i + group_size, total)
        group_str = ", ".join(str(x) for x in group)
        lines.append(f"   [{group_start}-{group_end}] {group_str}")

    return "\n" + "\n".join(lines)


def check_sequence_report(
    numbers, context_name="", mode="reset_1", prev_end=None, original_order=None
):
    """
    检查序列连续性并返回报告。
    Returns: (last_number, report_lines_list, missing_list)
    """
    if not numbers:
        return None, [], []

    unique_numbers = sorted(list(set(numbers)))
    start, end = unique_numbers[0], unique_numbers[-1]

    expected_start = None
    if mode == "reset_1":
        expected_start = 1
    elif mode == "reset_0":
        expected_start = 0
    elif mode == "continuous" and prev_end is not None:
        expected_start = prev_end + 1

    report = []
    status_icon = "✅"
    msg_prefix = ""

    if expected_start is not None and start != expected_start:
        msg_prefix = f"[起始错误: {start} (应为 {expected_start})]"
        status_icon = "⚠️ "

    full = set(range(start, end + 1))
    found = set(unique_numbers)
    missing = sorted(list(full - found))

    report.append(f"📌 {context_name}")

    if missing:
        formatted = format_missing_chapters(missing)
        report.append(f"   🔴 缺失 ({len(missing)} 章): {formatted}")
        report.append(f"   ℹ️  范围: {start} -> {end}")
    else:
        if msg_prefix:
            report.append(f"   {status_icon} 连续 {msg_prefix}")
        else:
            report.append(f"   {status_icon} 完整 ({start} -> {end})")

    # 检测顺序异常（如果提供了原始顺序）
    if original_order and len(original_order) > 1:
        order_issues = []
        for i in range(1, len(original_order)):
            prev_num = original_order[i - 1]
            curr_num = original_order[i]
            diff = curr_num - prev_num
            # 检测大跳跃（跳过超过1章）或倒退
            if diff > 1:
                order_issues.append(f"{prev_num}→{curr_num} (跳过{diff - 1}章)")
            elif diff < 0:
                order_issues.append(f"{prev_num}→{curr_num} (倒退)")

        if order_issues:
            report.append(f"   ⚠️  顺序异常 ({len(order_issues)} 处):")
            for issue in order_issues[:10]:
                report.append(f"      • {issue}")
            if len(order_issues) > 10:
                report.append(f"      ... 等 {len(order_issues)} 处")

    # 检测重复章节
    if len(numbers) != len(set(numbers)):
        from collections import Counter

        counter = Counter(numbers)
        duplicates = [(num, count) for num, count in counter.items() if count > 1]
        if duplicates:
            report.append(f"   ⚠️  重复章节 ({len(duplicates)} 个):")
            for num, count in duplicates[:5]:
                report.append(f"      • 第{num}章 出现{count}次")
            if len(duplicates) > 5:
                report.append(f"      ... 等 {len(duplicates)} 个")

    return end, report, missing


# 缺失章节占位符标记
MISSING_MARKER = "【★缺失★】"
MISSING_CLASS = "sigil-missing-chapter-placeholder"


def analyze_chapter_format(texts, config):
    """
    分析目录中章节的格式特征。
    返回: {
        'prefix': 前缀,
        'suffix': 后缀,
        'num_types': {'arabic': count, 'cn_lower': count, 'cn_upper': count},
        'has_volume': bool,
        'total_chapters': int,
        'sample_chapters': list,
    }
    """
    prefix = config["chap_prefix"]
    suffix = config["chap_suffix"]
    num_type = config.get("chap_num_type", "mixed")
    num_pat = NUM_PATTERNS.get(num_type, NUM_PATTERNS["mixed"])

    # 转义前缀和后缀，但保留后缀中的 '|' 逻辑
    escaped_prefix = re.escape(prefix)
    if "|" in suffix:
        # 如果包含 |，按 | 分割，转义每一部分后再合并
        parts = [re.escape(p.strip()) for p in suffix.split("|") if p.strip()]
        real_suffix = f"(?:{'|'.join(parts)})"
    else:
        real_suffix = re.escape(suffix)

    chap_regex_str = f"{escaped_prefix}\\s*({num_pat})\\s*{real_suffix}"
    vol_regex_str = config.get("vol_regex", "")

    try:
        chap_re = re.compile(chap_regex_str)
        vol_re = re.compile(vol_regex_str) if vol_regex_str else None
    except:
        return None

    num_types = {"arabic": 0, "cn_lower": 0, "cn_upper": 0, "variant": 0}
    sample_chapters = []
    has_volume = False

    cn_lower_chars = set("零〇一二三四五六七八九十百千万两")
    cn_upper_chars = set("壹贰叁肆伍陆柒捌玖拾佰仟萬")

    for t in texts:
        if vol_re and vol_re.search(t):
            has_volume = True
            continue

        cm = chap_re.search(t)
        if cm:
            num_str = cm.group(1)

            if num_str.isdigit():
                num_types["arabic"] += 1
            elif any(c in cn_upper_chars for c in num_str):
                num_types["cn_upper"] += 1
            elif any(c in cn_lower_chars for c in num_str):
                num_types["cn_lower"] += 1

            if "〇" in num_str or "两" in num_str:
                num_types["variant"] += 1

            if len(sample_chapters) < 5:
                sample_chapters.append(t.strip()[:30])

    total = sum(num_types.values()) - num_types["variant"]

    return {
        "prefix": prefix,
        "suffix": suffix,
        "num_types": num_types,
        "has_volume": has_volume,
        "total_chapters": total,
        "sample_chapters": sample_chapters,
    }


def get_chapter_info_from_nav(bk, config):
    """
    从 nav 中提取章节信息，返回 {章节号: href} 映射。
    """
    file_id, toc_type = get_toc_source(bk)
    if not file_id or toc_type != "nav":
        return None, None, {}

    content = bk.readfile(file_id)

    prefix = config["chap_prefix"]
    num_type = config.get("chap_num_type", "mixed")
    num_pat = NUM_PATTERNS.get(num_type, NUM_PATTERNS["mixed"])
    suffix = config["chap_suffix"]

    escaped_prefix = re.escape(prefix)
    if "|" in suffix:
        parts = [re.escape(p.strip()) for p in suffix.split("|") if p.strip()]
        real_suffix = f"(?:{'|'.join(parts)})"
    else:
        real_suffix = re.escape(suffix)
    chap_regex_str = f"{escaped_prefix}\\s*({num_pat})\\s*{real_suffix}"

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
    """
    找到缺失章节应该指向的 href（下一个存在的章节，如果没有则往上找）。
    """
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
    """
    在 nav.xhtml 中插入缺失章节的占位符。
    返回: (成功数, 错误信息)
    """
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
    """
    从 nav.xhtml 中删除所有缺失章节占位符。
    返回: (删除数, 错误信息)
    """
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


# --- GUI ---
class MainDialog(QDialog):
    def __init__(self, bk, config, parent=None):
        super().__init__(parent)
        self.bk = bk
        self.config = config
        self.setWindowTitle("章节缺失检查")
        self.resize(800, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 章节设置区域
        grp_chap = QGroupBox("章节设置")
        chap_layout = QVBoxLayout()

        # 第一行：前缀 + 数字类型 + 后缀
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("前缀:"))
        self.inp_prefix = QLineEdit(self.config.get("chap_prefix", ""))
        self.inp_prefix.setMinimumWidth(80)
        self.inp_prefix.setPlaceholderText("第")
        row1.addWidget(self.inp_prefix)
        row1.addSpacing(20)

        row1.addWidget(QLabel("数字类型:"))
        self.combo_num_type = QComboBox()
        self.combo_num_type.addItem("混合模式", "mixed")
        self.combo_num_type.addItem("阿拉伯数字", "arabic")
        self.combo_num_type.addItem("中文小写", "cn_lower")
        self.combo_num_type.addItem("中文大写", "cn_upper")
        current_type = self.config.get("chap_num_type", "mixed")
        for i in range(self.combo_num_type.count()):
            if self.combo_num_type.itemData(i) == current_type:
                self.combo_num_type.setCurrentIndex(i)
                break
        self.combo_num_type.setMinimumWidth(120)
        row1.addWidget(self.combo_num_type)
        row1.addStretch()
        chap_layout.addLayout(row1)

        # 第二行：后缀（下拉+自定义输入）
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("后缀:"))
        self.combo_suffix = QComboBox()
        self.combo_suffix.setEditable(True)
        self.combo_suffix.setMinimumWidth(100)
        custom_suffixes = self.config.get(
            "custom_suffixes", ["章", "回", "节", "话", "集"]
        )
        self.combo_suffix.addItems(custom_suffixes)
        current_suffix = self.config.get("chap_suffix", "章")
        idx = self.combo_suffix.findText(current_suffix)
        if idx >= 0:
            self.combo_suffix.setCurrentIndex(idx)
        else:
            self.combo_suffix.setCurrentText(current_suffix)
        row2.addWidget(self.combo_suffix)
        self.btn_add_suffix = QPushButton("添加后缀")
        self.btn_add_suffix.clicked.connect(self.add_custom_suffix)
        row2.addWidget(self.btn_add_suffix)
        row2.addStretch()

        # 编号模式
        row2.addWidget(QLabel("编号模式:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("每卷从1开始", "reset_1")
        self.combo_mode.addItem("每卷从0开始", "reset_0")
        self.combo_mode.addItem("全书连续", "continuous")
        current_mode = self.config.get("chap_reset_mode", "reset_1")
        for i in range(self.combo_mode.count()):
            if self.combo_mode.itemData(i) == current_mode:
                self.combo_mode.setCurrentIndex(i)
                break
        row2.addWidget(self.combo_mode)
        chap_layout.addLayout(row2)

        grp_chap.setLayout(chap_layout)
        layout.addWidget(grp_chap)

        # 卷/部设置区域
        grp_vol = QGroupBox("卷/部设置（可选）")
        vol_main = QVBoxLayout()

        # 第一行：启用卷检测 + 卷正则
        vol_row1 = QHBoxLayout()
        self.chk_enable_vol = QCheckBox("启用卷/部检测")
        self.chk_enable_vol.setChecked(self.config.get("enable_volume", False))
        vol_row1.addWidget(self.chk_enable_vol)
        vol_row1.addWidget(QLabel("卷正则:"))
        self.inp_vol_regex = QLineEdit(self.config.get("vol_regex", ""))
        self.inp_vol_regex.setPlaceholderText(
            "第\\s*([0-9]+|[零〇一二三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟萬两]+)\\s*[卷部]"
        )
        self.inp_vol_regex.setEnabled(self.chk_enable_vol.isChecked())
        self.chk_enable_vol.toggled.connect(self.inp_vol_regex.setEnabled)
        vol_row1.addWidget(self.inp_vol_regex, 1)
        vol_main.addLayout(vol_row1)

        # 第二行：自动检测章节重置
        vol_row2 = QHBoxLayout()
        self.chk_auto_reset = QCheckBox(
            "自动检测章节重置（无卷标题时，章节号从大变小自动分段）"
        )
        self.chk_auto_reset.setChecked(self.config.get("auto_detect_reset", False))
        vol_row2.addWidget(self.chk_auto_reset)
        vol_row2.addStretch()
        vol_main.addLayout(vol_row2)

        grp_vol.setLayout(vol_main)
        layout.addWidget(grp_vol)

        # 按钮栏
        btn_layout = QHBoxLayout()
        self.btn_check = QPushButton("开始检查")
        self.btn_check.setMinimumHeight(36)
        self.btn_check.setMinimumWidth(100)
        self.btn_check.clicked.connect(self.do_check)
        self.btn_save = QPushButton("保存设置")
        self.btn_save.setMinimumHeight(36)
        self.btn_save.clicked.connect(self.do_save)

        btn_layout.addWidget(self.btn_check)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addSpacing(20)

        # 缺失章节操作按钮
        self.btn_insert = QPushButton("插入缺失占位")
        self.btn_insert.setMinimumHeight(36)
        self.btn_insert.setToolTip(
            f"在 nav 目录中插入缺失章节占位符\n标记: {MISSING_MARKER}"
        )
        self.btn_insert.clicked.connect(self.do_insert_missing)
        self.btn_remove = QPushButton("删除占位符")
        self.btn_remove.setMinimumHeight(36)
        self.btn_remove.setToolTip(f"删除所有带 {MISSING_MARKER} 标记的占位符")
        self.btn_remove.clicked.connect(self.do_remove_placeholders)

        btn_layout.addWidget(self.btn_insert)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addStretch()

        self.btn_close = QPushButton("关闭")
        self.btn_close.setMinimumHeight(36)
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

        # 结果显示区域
        grp_result = QGroupBox("检查结果")
        result_layout = QVBoxLayout()
        self.text_result = QTextEdit()
        self.text_result.setReadOnly(True)
        font = QFont()
        font.setPointSize(12)
        self.text_result.setFont(font)
        self.text_result.setPlaceholderText("点击「开始检查」查看结果...")
        result_layout.addWidget(self.text_result)
        grp_result.setLayout(result_layout)
        layout.addWidget(grp_result, 1)

        self.setLayout(layout)

    def add_custom_suffix(self):
        current = self.combo_suffix.currentText().strip()
        if current and self.combo_suffix.findText(current) < 0:
            self.combo_suffix.addItem(current)
            self.text_result.setPlainText(f"✅ 已添加后缀「{current}」")

    def get_config(self):
        suffixes = [
            self.combo_suffix.itemText(i) for i in range(self.combo_suffix.count())
        ]
        return {
            "chap_prefix": self.inp_prefix.text(),
            "chap_num_type": self.combo_num_type.currentData(),
            "chap_suffix": self.combo_suffix.currentText(),
            "custom_suffixes": suffixes,
            "enable_volume": self.chk_enable_vol.isChecked(),
            "vol_regex": self.inp_vol_regex.text(),
            "chap_reset_mode": self.combo_mode.currentData(),
            "auto_detect_reset": self.chk_auto_reset.isChecked(),
        }

    def do_save(self):
        new_config = self.get_config()
        save_config(new_config)
        self.config = new_config
        self.text_result.setPlainText("✅ 设置已保存")

    def do_check(self):
        new_config = self.get_config()
        save_config(new_config)
        self.config = new_config
        result_text, missing = perform_check(self.bk, new_config)
        self.last_missing = missing
        self.text_result.setPlainText(result_text)

    def do_insert_missing(self):
        if not hasattr(self, "last_missing") or not self.last_missing:
            self.text_result.setPlainText("⚠️ 请先点击「开始检查」获取缺失章节列表")
            return

        reply = QMessageBox.question(
            self,
            "确认插入",
            f"将在 nav 目录中插入 {len(self.last_missing)} 个缺失章节占位符。\n\n"
            f"标记格式: {MISSING_MARKER}第X章\n"
            f"占位符将指向最近的现有章节。\n\n"
            f"确定继续?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            config = self.get_config()
            count, err = insert_missing_chapters_to_nav(
                self.bk, config, self.last_missing
            )
            if err:
                self.text_result.setPlainText(f"❌ 插入失败: {err}")
            else:
                self.text_result.setPlainText(
                    f"✅ 已插入 {count} 个缺失章节占位符\n\n"
                    f"标记: {MISSING_MARKER}\n"
                    f"类名: {MISSING_CLASS}\n\n"
                    f"可随时使用「删除占位符」按钮移除"
                )

    def do_remove_placeholders(self):
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"将删除 nav 目录中所有带 {MISSING_MARKER} 标记的占位符。\n\n确定继续?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            count, err = remove_missing_placeholders(self.bk)
            if err:
                self.text_result.setPlainText(f"❌ 删除失败: {err}")
            elif count == 0:
                self.text_result.setPlainText("ℹ️ 未找到需要删除的占位符")
            else:
                self.text_result.setPlainText(f"✅ 已删除 {count} 个占位符")


# --- Main Logic ---
def split_by_reset(chapters):
    """
    将章节列表按重置点分割成多个段。
    当章节号从大变小（如 30 -> 1）时认为是新的一段。
    """
    if not chapters:
        return []

    segments = []
    current_segment = [chapters[0]]

    for i in range(1, len(chapters)):
        if chapters[i] < chapters[i - 1]:
            segments.append(current_segment)
            current_segment = [chapters[i]]
        else:
            current_segment.append(chapters[i])

    if current_segment:
        segments.append(current_segment)

    return segments


def perform_check(bk, config):
    prefix = config["chap_prefix"]
    suffix = config["chap_suffix"]
    num_type = config.get("chap_num_type", "mixed")
    num_pat = NUM_PATTERNS.get(num_type, NUM_PATTERNS["mixed"])

    escaped_prefix = re.escape(prefix)
    if "|" in suffix:
        parts = [re.escape(p.strip()) for p in suffix.split("|") if p.strip()]
        real_suffix = f"(?:{'|'.join(parts)})"
    else:
        real_suffix = re.escape(suffix)

    chap_regex_str = f"{escaped_prefix}\\s*({num_pat})\\s*{real_suffix}"
    enable_vol = config["enable_volume"]
    vol_regex_str = config["vol_regex"]
    mode = config["chap_reset_mode"]
    auto_detect_reset = config.get("auto_detect_reset", False)

    file_id, toc_type = get_toc_source(bk)
    toc_info = f"{toc_type.upper()}" if toc_type else "未找到"

    report_lines = []

    # 输出配置信息
    report_lines.append("=" * 50)
    report_lines.append("📋 检测配置")
    report_lines.append("=" * 50)
    report_lines.append(f"   前缀: 「{prefix}」")
    report_lines.append(f"   后缀: 「{suffix}」")
    report_lines.append(f"   数字类型: {NUM_TYPE_NAMES.get(num_type, num_type)}")
    report_lines.append(f"   目录来源: {toc_info}")
    mode_str = "按卷" if enable_vol else ("自动分段" if auto_detect_reset else "全书")
    report_lines.append(f"   检测模式: {mode_str}")
    if enable_vol:
        report_lines.append(f"   卷正则: {vol_regex_str}")
    report_lines.append("")

    try:
        chap_re = re.compile(chap_regex_str)
        vol_re = re.compile(vol_regex_str) if (enable_vol and vol_regex_str) else None
    except Exception as e:
        return f"❌ 正则错误: {e}"

    texts = get_nav_texts(bk)
    if not texts:
        return "❌ 错误: 无法找到或解析目录文件 (nav.xhtml/toc.ncx)", []

    # 分析章节格式
    analysis = analyze_chapter_format(texts, config)
    if analysis:
        report_lines.append("=" * 50)
        report_lines.append("📊 目录分析")
        report_lines.append("=" * 50)
        report_lines.append(f"   识别章节数: {analysis['total_chapters']}")

        nt = analysis["num_types"]
        type_parts = []
        if nt["arabic"] > 0:
            type_parts.append(f"阿拉伯数字 {nt['arabic']}")
        if nt["cn_lower"] > 0:
            type_parts.append(f"中文小写 {nt['cn_lower']}")
        if nt["cn_upper"] > 0:
            type_parts.append(f"中文大写 {nt['cn_upper']}")
        if type_parts:
            report_lines.append(f"   数字分布: {', '.join(type_parts)}")

        if nt["variant"] > 0:
            report_lines.append(f"   变体字符: 有 ({nt['variant']} 处，含〇或两)")
        else:
            report_lines.append(f"   变体字符: 无")

        report_lines.append(
            f"   检测到分卷: {'是' if analysis['has_volume'] else '否'}"
        )

        if analysis["sample_chapters"]:
            report_lines.append(f"   示例章节:")
            for s in analysis["sample_chapters"][:3]:
                report_lines.append(f"      • {s}")
        report_lines.append("")

    report_lines.append("=" * 50)
    report_lines.append("🔍 检查结果")
    report_lines.append("=" * 50)

    data = {}
    volume_order = []
    current_vol = 0
    all_chapters_ordered = []

    if enable_vol and vol_re:
        current_vol = -1
    else:
        data[0] = []
        volume_order.append(0)

    for t in texts:
        if enable_vol and vol_re:
            vm = vol_re.search(t)
            if vm:
                try:
                    if vm.groups():
                        v_num = cn2an_simple(vm.group(1))
                    else:
                        v_num = len(volume_order) + 1
                    current_vol = v_num
                    if current_vol not in data:
                        data[current_vol] = []
                        volume_order.append(current_vol)
                    continue
                except:
                    pass

        cm = chap_re.search(t)
        if cm:
            try:
                c_num = cn2an_simple(cm.group(1))
                all_chapters_ordered.append(c_num)
                target_vol = current_vol
                if target_vol == -1:
                    target_vol = 0
                if target_vol not in data:
                    data[target_vol] = []
                    if target_vol not in volume_order:
                        volume_order.append(target_vol)
                data[target_vol].append(c_num)
            except:
                pass

    all_missing = []

    # 自动检测章节重置模式
    if auto_detect_reset and not enable_vol and all_chapters_ordered:
        segments = split_by_reset(all_chapters_ordered)
        if len(segments) > 1:
            report_lines.append(f"📊 检测到 {len(segments)} 个分段（章节号重置点）")
            report_lines.append("-" * 20)

            has_content = False
            for idx, seg in enumerate(segments, 1):
                if not seg:
                    continue
                has_content = True
                name = f"📑 分段 {idx}"
                _, r, missing = check_sequence_report(
                    seg, name, mode=mode, prev_end=None, original_order=seg
                )
                report_lines.extend(r)
                all_missing.extend(missing)

            if not has_content:
                report_lines.append("⚠️  未找到匹配的章节")

            return "\n".join(report_lines), all_missing

    if enable_vol and len(volume_order) > 0:
        real_vols = [v for v in volume_order if v != 0]
        if real_vols:
            _, r, _ = check_sequence_report(real_vols, "📚 卷序列", mode="reset_1")
            report_lines.extend(r)
            report_lines.append("-" * 20)

    prev_end = 0
    has_content = False

    for vol in volume_order:
        chapters = data.get(vol, [])
        if not chapters:
            continue

        has_content = True
        if vol == 0 and not enable_vol:
            name = "📖 全书"
        elif vol == 0:
            name = "📂 未分类"
        else:
            name = f"📑 第 {vol} 卷"

        current_mode = mode
        if mode == "continuous" and vol == volume_order[0]:
            prev_end = 0

        last_chap, r, missing = check_sequence_report(
            chapters,
            name,
            mode=current_mode,
            prev_end=prev_end,
            original_order=chapters,
        )
        report_lines.extend(r)
        all_missing.extend(missing)

        if last_chap is not None:
            prev_end = last_chap

    if not has_content:
        report_lines.append("⚠️  未找到匹配的章节")
        report_lines.append("   -> 请检查设置是否正确")
        if not file_id:
            report_lines.append("   -> 未在 EPUB 中找到 nav.xhtml 或 toc.ncx")

    return "\n".join(report_lines), all_missing


def run(bk):
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    config = load_or_create_config()
    dlg = MainDialog(bk, config)
    dlg.exec_()

    return 0
