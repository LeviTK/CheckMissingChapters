import re

CN_NUM_LOWER = "零〇一二三四五六七八九十百千万两"
CN_NUM_UPPER = "壹贰叁肆伍陆柒捌玖拾佰仟萬"
CN_NUM_ALL = CN_NUM_LOWER + CN_NUM_UPPER
DIGIT_PATTERN = r"[0-9０-９]"

NUM_PATTERNS = {
    "mixed": rf"(?:{DIGIT_PATTERN}(?:\s*{DIGIT_PATTERN})*|[{CN_NUM_ALL}](?:\s*[{CN_NUM_ALL}])*)",
    "arabic": rf"{DIGIT_PATTERN}(?:\s*{DIGIT_PATTERN})*",
    "cn_lower": rf"[{CN_NUM_LOWER}](?:\s*[{CN_NUM_LOWER}])*",
    "cn_upper": rf"[{CN_NUM_UPPER}](?:\s*[{CN_NUM_UPPER}])*",
}

NUM_TYPE_NAMES = {
    "mixed": "混合模式",
    "arabic": "阿拉伯数字",
    "cn_lower": "中文小写",
    "cn_upper": "中文大写",
}

FULLWIDTH_DIGIT_MAP = str.maketrans("０１２３４５６７８９", "0123456789")


def normalize_number_text(text):
    if not text:
        return ""
    text = text.translate(FULLWIDTH_DIGIT_MAP)
    text = re.sub(r"\s+", "", text)
    return text


def cn2an_simple(text):
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

    text = normalize_number_text(text)
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
