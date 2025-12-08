import sys
import re
import os
import json
import xml.etree.ElementTree as ET
from pyqt_import import *

# --- Configuration File ---
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

# Expanded config structure
DEFAULT_CONFIG = {
    "chap_prefix": "第",
    "chap_num_pattern": r"[0-9]+|[零一二三四五六七八九十百千万]+",
    "chap_suffix": "章",
    
    "enable_volume": False,
    "vol_regex": r"第\s*([0-9]+|[零一二三四五六七八九十百千万]+)\s*[卷部]",
    
    # reset_1 (Each volume starts at 1), reset_0 (starts at 0), continuous (continues from prev volume)
    "chap_reset_mode": "reset_1" 
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                # Merge with default to ensure all keys exist
                data = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except:
        pass

# --- Chinese Number Conversion ---
def cn2an_simple(text):
    cn_nums = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, 
               '六': 6, '七': 7, '八': 8, '九': 9}
    cn_units = {'十': 10, '百': 100, '千': 1000, '万': 10000}

    if text.isdigit():
        return int(text)

    if len(text) == 1 and text in cn_nums:
        return cn_nums[text]

    result = 0
    temp_val = 0
    current_val = 0
    
    for char in text:
        if char in cn_nums:
            current_val = cn_nums[char]
        elif char in cn_units:
            unit_val = cn_units[char]
            if current_val == 0 and unit_val == 10: 
                current_val = 1
            
            if unit_val > temp_val and temp_val > 0:
                 result += (temp_val + current_val) * unit_val
                 temp_val = 0
                 current_val = 0
            else:
                 temp_val += current_val * unit_val
                 current_val = 0
    
    result += temp_val + current_val
    return result

# --- UI Class ---
class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Missing Chapters Settings")
        self.config = config
        self.setup_ui()
        self.resize(400, 350)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Group 1: Chapter Rules (3 Rows) ---
        gb_chap = QGroupBox("章节规则 (Chapter Rules)")
        layout_chap = QVBoxLayout()
        
        # Row 1: Prefix
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("前缀 (Prefix):"))
        self.le_prefix = QLineEdit(self.config.get("chap_prefix", ""))
        self.le_prefix.setPlaceholderText("例如: 第")
        row1.addWidget(self.le_prefix)
        layout_chap.addLayout(row1)

        # Row 2: Number Pattern
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("数字 (Number):"))
        self.cb_num = QComboBox()
        self.cb_num.setEditable(True)
        # Preset patterns
        self.cb_num.addItem(r"[0-9]+", "仅阿拉伯数字")
        self.cb_num.addItem(r"[零一二三四五六七八九十百千万]+", "仅中文数字")
        self.cb_num.addItem(r"[0-9]+|[零一二三四五六七八九十百千万]+", "混合支持")
        # Set current text
        self.cb_num.setEditText(self.config.get("chap_num_pattern", ""))
        row2.addWidget(self.cb_num)
        layout_chap.addLayout(row2)

        # Row 3: Suffix
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("后缀 (Suffix):"))
        self.le_suffix = QLineEdit(self.config.get("chap_suffix", ""))
        self.le_suffix.setPlaceholderText("例如: 章 OR 章|节|回")
        self.le_suffix.setToolTip("支持多选，如 '章|节' (Support regex OR like '章|节')")
        row3.addWidget(self.le_suffix)
        layout_chap.addLayout(row3)
        
        gb_chap.setLayout(layout_chap)
        main_layout.addWidget(gb_chap)

        # --- Group 2: Volume Rules (1 Row + details) ---
        gb_vol = QGroupBox("分卷规则 (Volume Rules)")
        layout_vol = QVBoxLayout()
        
        # Checkbox & Regex
        row_v1 = QHBoxLayout()
        self.chk_vol = QCheckBox("启用分卷 (Enable)")
        self.chk_vol.setChecked(self.config.get("enable_volume", False))
        self.chk_vol.stateChanged.connect(self.toggle_vol_options)
        row_v1.addWidget(self.chk_vol)
        
        self.le_vol_regex = QLineEdit(self.config.get("vol_regex", ""))
        self.le_vol_regex.setPlaceholderText("例如: 第([0-9]+)卷")
        row_v1.addWidget(self.le_vol_regex)
        layout_vol.addLayout(row_v1)
        
        # Reset Mode
        row_v2 = QHBoxLayout()
        row_v2.addWidget(QLabel("编号策略 (Mode):"))
        self.cb_reset = QComboBox()
        self.cb_reset.addItem("每卷重置为 1 (Reset to 1)", "reset_1")
        self.cb_reset.addItem("每卷重置为 0 (Reset to 0)", "reset_0")
        self.cb_reset.addItem("接续上一卷 (Continuous)", "continuous")
        
        # Select current
        curr_mode = self.config.get("chap_reset_mode", "reset_1")
        idx = self.cb_reset.findData(curr_mode)
        if idx >= 0:
            self.cb_reset.setCurrentIndex(idx)
            
        row_v2.addWidget(self.cb_reset)
        layout_vol.addLayout(row_v2)
        
        gb_vol.setLayout(layout_vol)
        main_layout.addWidget(gb_vol)

        self.toggle_vol_options() # Init state

        # --- Buttons ---
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        main_layout.addWidget(bbox)

    def toggle_vol_options(self):
        enabled = self.chk_vol.isChecked()
        self.le_vol_regex.setEnabled(enabled)
        self.cb_reset.setEnabled(enabled)

    def get_settings(self):
        return {
            "chap_prefix": self.le_prefix.text(),
            "chap_num_pattern": self.cb_num.currentText(),
            "chap_suffix": self.le_suffix.text(),
            "enable_volume": self.chk_vol.isChecked(),
            "vol_regex": self.le_vol_regex.text(),
            "chap_reset_mode": self.cb_reset.currentData()
        }

# --- Core Logic ---
def get_nav_texts(bk):
    nav_id = None
    try:
        if hasattr(bk, 'manifest_iter'):
            iterator = bk.manifest_iter()
        else:
            iterator = []
        for file_id in iterator:
            if hasattr(bk, 'id_to_href'):
                href = bk.id_to_href(file_id)
                if href and 'nav.xhtml' in href.lower(): 
                    nav_id = file_id
                    break
    except:
        pass
    
    if not nav_id:
        for p in ['Text/nav.xhtml', 'OEBPS/nav.xhtml', 'nav.xhtml']:
             if bk.href_to_id(p):
                 nav_id = bk.href_to_id(p)
                 break

    if not nav_id:
        print("Error: 无法找到导航文档 (nav.xhtml).")
        return []

    content = bk.readfile(nav_id)
    
    texts = []
    try:
        content = re.sub(r' xmlns="[^"]+"', '', content, count=1)
        root = ET.fromstring(content)
        for elem in root.iter():
            if elem.text and elem.text.strip():
                texts.append(elem.text.strip())
            if elem.tail and elem.tail.strip():
                texts.append(elem.tail.strip())
    except:
        matches = re.findall(r'>([^<]+)<', content)
        texts = [m.strip() for m in matches if m.strip()]
    
    return texts

def check_sequence(numbers, context_name="", mode="reset_1", prev_end=None):
    if not numbers:
        return None
    
    numbers = sorted(list(set(numbers)))
    start, end = numbers[0], numbers[-1]
    
    full_range_start = start
    
    # Mode Check
    expected_start = None
    if mode == "reset_1":
        expected_start = 1
    elif mode == "reset_0":
        expected_start = 0
    elif mode == "continuous" and prev_end is not None:
        expected_start = prev_end + 1
    
    msg_prefix = ""
    if expected_start is not None and start != expected_start:
        msg_prefix = f"[警告: 起始号 {start} (预期 {expected_start})] "
        # If we just want to check gaps, we use start...end
        # If we want to check absolute correctness, we should check range(expected_start, end+1)
        # But usually users care about GAPS mostly.
        # However, if it starts at 5, we should probably warn.
    
    full = set(range(start, end + 1))
    found = set(numbers)
    missing = sorted(list(full - found))
    
    if missing:
        msg_list = [str(x) for x in missing]
        trunc_msg = ", ".join(msg_list[:20]) + ("..." if len(msg_list)>20 else "")
        print(f"⚠️  {context_name} {msg_prefix}")
        print(f"    范围: {start}-{end} | 缺失: {trunc_msg} (共 {len(missing)} 处)")
    else:
        if msg_prefix:
            print(f"⚠️  {context_name} {msg_prefix} - 但中间无间断")
        else:
            print(f"✅  {context_name} [范围: {start}-{end}] - 完美连续")
            
    return end

def run(bk):
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    config = load_config()
    dlg = SettingsDialog(config)
    if dlg.exec() != QDialog.Accepted:
        return 0
    
    new_settings = dlg.get_settings()
    save_config(new_settings)
    
    # Build Regex
    # Chapter: prefix + \s* + (num) + \s* + suffix
    # If suffix contains |, wrap in (?:) if not already
    prefix = new_settings["chap_prefix"]
    num_pat = new_settings["chap_num_pattern"]
    suffix = new_settings["chap_suffix"]
    
    # Smart suffix wrapping if needed
    if "|" in suffix and not suffix.startswith("(") and not suffix.startswith("["):
        real_suffix = f"(?:{suffix})"
    else:
        real_suffix = suffix
        
    # Note: prefix usually literal, but user might want regex. We assume user knows regex if they type special chars?
    # Let's treat prefix/suffix as Regex parts (user request implies customization)
    chap_regex_str = f"{prefix}\s*({num_pat})\s*{real_suffix}"
    
    enable_vol = new_settings["enable_volume"]
    vol_regex_str = new_settings["vol_regex"]
    mode = new_settings["chap_reset_mode"]

    try:
        chap_re = re.compile(chap_regex_str)
        vol_re = re.compile(vol_regex_str) if (enable_vol and vol_regex_str) else None
    except Exception as e:
        print(f"Error: 正则表达式构建失败:\n{e}")
        return 0

    texts = get_nav_texts(bk)
    if not texts:
        print("未找到导航文本。")
        return 0

    # Data Collection
    data = {} # { vol_num: [chap_nums] }
    volume_order = [] 
    current_vol = 0
    
    if enable_vol and vol_re:
        current_vol = -1 # Start in "void"
    else:
        # Global mode
        data[0] = []
        volume_order.append(0)
        
    print("\n" + "="*50)
    print(f"检查配置:")
    print(f"  • 章节正则: {chap_regex_str}")
    if enable_vol:
        print(f"  • 分卷模式: {mode} (正则: {vol_regex_str})")
    else:
        print(f"  • 分卷: 未启用")
    print("="*50 + "\n")

    for t in texts:
        # Check Volume
        if enable_vol and vol_re:
            vm = vol_re.search(t)
            if vm:
                try:
                    # Try to extract number if group exists, else just count?
                    # Usually regex has group 1.
                    if vm.groups():
                        v_num = cn2an_simple(vm.group(1))
                    else:
                        # If no number captured, auto-increment internal counter
                        # But user might have irregular strings.
                        # Let's assume user follows prompt hint to include group.
                        v_num = len(volume_order) + 1 
                    
                    current_vol = v_num
                    if current_vol not in data:
                        data[current_vol] = []
                        volume_order.append(current_vol)
                    continue
                except:
                    pass

        # Check Chapter
        cm = chap_re.search(t)
        if cm:
            try:
                c_num = cn2an_simple(cm.group(1))
                
                target_vol = current_vol
                # If "Void" (-1), maybe assign to 0 (Uncategorized)
                if target_vol == -1:
                    target_vol = 0
                
                if target_vol not in data:
                    data[target_vol] = []
                    if target_vol not in volume_order:
                        volume_order.append(target_vol)
                
                data[target_vol].append(c_num)
            except:
                pass

    # Analysis
    
    # Volume Sequence Check
    if enable_vol and len(volume_order) > 0:
        # Check if volume numbers themselves are continuous
        # Only if we actually captured numbers (not just auto-gen)
        # Assuming user regex captures numbers.
        real_vols = [v for v in volume_order if v != 0]
        if real_vols:
             # Simple check for volumes: they usually start at 1 and are continuous
             # But "Volume 1" might be implied.
             check_sequence(real_vols, "分卷序列 (Volumes)", mode="reset_1") # Volumes usually reset_1
        else:
             print("ℹ️  检测到分卷但未捕获有效卷号 (可能未归类)。")
             
    prev_end = 0
    has_content = False
    
    for vol in volume_order:
        chapters = data[vol]
        if not chapters:
            continue
        has_content = True
        
        if vol == 0 and not enable_vol:
            name = "整书"
        elif vol == 0:
            name = "未归类部分"
        else:
            name = f"第 {vol} 卷/部"
            
        # Determine effective mode for this section
        # If "Uncategorized" (vol 0) appears at start, it acts like start of book -> reset_1 usually?
        # Or if mode is continuous, it starts at 1.
        
        current_mode = mode
        if vol == volume_order[0] and mode == "continuous":
            # First volume in continuous mode starts at 1 (or 0?)
            # Let's treat it as reset_1 for the very first block unless specified
            # Actually, standard check_sequence handles "expected_start"
            # If continuous, prev_end starts at 0.
            pass
            
        last_chap = check_sequence(chapters, name, mode=current_mode, prev_end=prev_end)
        
        if last_chap is not None:
            prev_end = last_chap

    if not has_content:
        print("⚠️  未提取到任何章节。请检查前缀/数字/后缀设置。")

    print("\n" + "="*50)
    return 0
