from pyqt_import import *

from config import DEFAULT_VOL_REGEX, load_or_create_config, save_config
from constants import MISSING_CLASS, MISSING_MARKER
from report import perform_check
from toc import insert_missing_chapters_to_nav, remove_missing_placeholders


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

        grp_chap = QGroupBox("章节设置")
        chap_layout = QVBoxLayout()

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

        grp_vol = QGroupBox("卷/部设置（可选）")
        vol_main = QVBoxLayout()

        vol_row1 = QHBoxLayout()
        self.chk_enable_vol = QCheckBox("启用卷/部检测")
        self.chk_enable_vol.setChecked(self.config.get("enable_volume", False))
        vol_row1.addWidget(self.chk_enable_vol)
        vol_row1.addWidget(QLabel("卷正则:"))
        self.inp_vol_regex = QLineEdit(self.config.get("vol_regex", ""))
        self.inp_vol_regex.setPlaceholderText(DEFAULT_VOL_REGEX)
        self.inp_vol_regex.setEnabled(self.chk_enable_vol.isChecked())
        self.chk_enable_vol.toggled.connect(self.inp_vol_regex.setEnabled)
        vol_row1.addWidget(self.inp_vol_regex, 1)
        vol_main.addLayout(vol_row1)

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
        suffixes = [self.combo_suffix.itemText(i) for i in range(self.combo_suffix.count())]
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
            count, err = insert_missing_chapters_to_nav(self.bk, config, self.last_missing)
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


def run(bk):
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    config = load_or_create_config()
    dlg = MainDialog(bk, config)
    dlg.exec_()

    return 0
