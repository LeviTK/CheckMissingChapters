import os
import sys

# Get Sigil Qt version from environment or default to 6
e = os.environ.get('SIGIL_QT_RUNTIME_VERSION', '6')
try:
    SIGIL_QT_MAJOR_VERSION = int(e.split(".")[0])
except ValueError:
    SIGIL_QT_MAJOR_VERSION = 6

if SIGIL_QT_MAJOR_VERSION == 6:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtWidgets import *
    from PySide6.QtCore import *
    from PySide6.QtGui import *
elif SIGIL_QT_MAJOR_VERSION == 5:
    from PyQt5 import QtWidgets, QtCore, QtGui
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
else:
    # Fallback
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtWidgets import *
    from PySide6.QtCore import *
    from PySide6.QtGui import *
