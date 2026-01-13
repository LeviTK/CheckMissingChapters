import re

from config import build_chapter_regex_str
from num_utils import (
    CN_NUM_LOWER,
    CN_NUM_UPPER,
    NUM_TYPE_NAMES,
    cn2an_simple,
    normalize_number_text,
)
from toc import get_nav_texts


def format_missing_chapters(missing, group_size=30):
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

    if original_order and len(original_order) > 1:
        order_issues = []
        for i in range(1, len(original_order)):
            prev_num = original_order[i - 1]
            curr_num = original_order[i]
            diff = curr_num - prev_num
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


def split_by_reset(chapters):
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


def analyze_chapter_format(texts, config):
    prefix = config["chap_prefix"]
    suffix = config["chap_suffix"]
    chap_regex_str = build_chapter_regex_str(config)
    vol_regex_str = config.get("vol_regex", "")

    try:
        chap_re = re.compile(chap_regex_str)
        vol_re = re.compile(vol_regex_str) if vol_regex_str else None
    except:
        return None

    num_types = {"arabic": 0, "cn_lower": 0, "cn_upper": 0, "variant": 0}
    sample_chapters = []
    has_volume = False

    cn_lower_chars = set(CN_NUM_LOWER)
    cn_upper_chars = set(CN_NUM_UPPER)

    for t in texts:
        if vol_re and vol_re.search(t):
            has_volume = True
            continue

        cm = chap_re.search(t)
        if cm:
            num_str = normalize_number_text(cm.group(1))

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


def perform_check(bk, config):
    prefix = config["chap_prefix"]
    num_type = config.get("chap_num_type", "mixed")
    suffix = config["chap_suffix"]

    chap_regex_str = build_chapter_regex_str(config)
    enable_vol = config["enable_volume"]
    vol_regex_str = config["vol_regex"]
    mode = config["chap_reset_mode"]
    auto_detect_reset = config.get("auto_detect_reset", False)

    file_id, toc_type = bk and __safe_get_toc(bk) or (None, None)
    toc_info = f"{toc_type.upper()}" if toc_type else "未找到"

    report_lines = []

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
        return f"❌ 正则错误: {e}", []

    texts = get_nav_texts(bk)
    if not texts:
        return "❌ 错误: 无法找到或解析目录文件 (nav.xhtml/toc.ncx)", []

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


def __safe_get_toc(bk):
    try:
        from toc import get_toc_source

        return get_toc_source(bk)
    except Exception:
        return None, None
