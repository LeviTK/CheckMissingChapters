import sys
import os

# Sigil Plugin Wrapper for Qt compatibility
# Tries to import PyQt5, then PySide6, then PySide2

wrapper_loaded = False

try:
    from PyQt5 import QtWidgets, QtCore, QtGui
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *

    wrapper_loaded = True
    QT_VERSION = 5
except ImportError:
    pass

if not wrapper_loaded:
    try:
        from PySide6 import QtWidgets, QtCore, QtGui
        from PySide6.QtWidgets import *
        from PySide6.QtCore import *
        from PySide6.QtGui import *

        wrapper_loaded = True
        QT_VERSION = 6
    except ImportError:
        pass

if not wrapper_loaded:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
        from PySide2.QtWidgets import *
        from PySide2.QtCore import *
        from PySide2.QtGui import *

        wrapper_loaded = True
        QT_VERSION = 2
    except ImportError:
        pass

if not wrapper_loaded:
    raise ImportError(
        "CheckMissingChapters Plugin: Could not find PyQt5, PySide6, or PySide2."
    )
