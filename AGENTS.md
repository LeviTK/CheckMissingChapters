# Sigil 插件开发指南

## 构建与测试
- **环境**：Sigil 内嵌 Python 3.4+。
- **运行**：将 `src` 文件夹内的文件打包为 `.zip`（注意：压缩文件夹内容，而非文件夹本身），通过 Sigil > 插件 > 管理插件 安装。
- **测试**：仅支持手动验证，无自动化测试套件。
- **调试**：使用 `print()` 语句，输出显示在 Sigil 的插件运行器窗口中。

## 代码风格
- **缩进**：使用 4 个空格。
- **命名**：函数/变量使用 `snake_case`，类使用 `PascalCase`，常量使用 `UPPER_CASE`。
- **导入顺序**：标准库优先，其次第三方库（如 Qt），最后本地模块（`pyqt_import`）。
- **类型标注**：使用动态类型，不使用 type hints。
- **异常处理**：使用具体的 `try...except` 块并指定异常类型，错误信息通过 `print()` 输出到插件控制台，避免宿主应用崩溃。
- **界面**：始终从 `pyqt_import` 导入 Qt 类，确保跨版本兼容。
- **结构**：入口函数为 `run(bk)`；源码位于 `src/`，核心逻辑分布在各模块中。

## 项目结构
```
src/
├── plugin.py        # 入口，导入 ui.run
├── plugin.xml       # 插件配置
├── pyqt_import.py   # Qt 兼容层（PyQt5/PySide6/PySide2）
├── config.py        # 配置持久化与章节正则构建
├── constants.py     # 共享常量
├── num_utils.py     # 数字转换（全角、中文、阿拉伯）
├── toc.py           # TOC 发现、解析与 nav.xhtml 修改
├── report.py        # 检测逻辑与报告生成
└── ui.py            # Qt 对话框与用户交互
docs/
└── CHANGELOG.md     # 版本变更记录
```
