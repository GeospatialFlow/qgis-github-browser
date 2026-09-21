# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later
"""
Message boxes that always show plain text. File names, repository names and
error messages come from GitHub, so they must never be interpreted as HTML
(no spoofed dialogs, no clickable links).
"""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox


def _show(parent, icon, title, text, buttons=QMessageBox.Ok, default=None):
    box = QMessageBox(icon, title, text, buttons, parent)
    box.setTextFormat(Qt.PlainText)
    if default is not None:
        box.setDefaultButton(default)
    return box.exec_()


def notify(parent, title, text):
    _show(parent, QMessageBox.Information, title, text)


def warn(parent, title, text):
    _show(parent, QMessageBox.Warning, title, text)


def ask(parent, title, text):
    """Yes/No question with No as the default. Returns True for Yes."""
    answer = _show(
        parent, QMessageBox.Question, title, text,
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
    )
    return answer == QMessageBox.Yes
