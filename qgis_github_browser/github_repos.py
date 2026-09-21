# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later
"""
Repository picker: lists every repository the saved token can access
(private ones included) in a multi-select dialog, so repos do not have
to be typed by hand.
"""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QDialogButtonBox,
)


def fetch_user_repos(api_get, token, per_page=100, max_pages=30):
    """Returns [(full_name, is_private), ...] sorted by name. Follows
    pagination (100 repos per page) until the last page."""
    repos = []
    for page in range(1, max_pages + 1):
        batch = api_get(
            f"https://api.github.com/user/repos?per_page={per_page}&page={page}",
            token,
        )
        repos.extend((r["full_name"], bool(r.get("private"))) for r in batch)
        if len(batch) < per_page:
            break
    return sorted(repos, key=lambda r: r[0].lower())


class RepoPickerDialog(QDialog):
    def __init__(self, parent, available, current):
        super().__init__(parent)
        self.setWindowTitle("Select Repositories")
        self.resize(420, 480)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"{len(available)} repositories found. Tick the ones to show in the panel:"))

        self.ed_filter = QLineEdit()
        self.ed_filter.setPlaceholderText("filter...")
        self.ed_filter.textChanged.connect(self._apply_filter)
        lay.addWidget(self.ed_filter)

        self.list = QListWidget()
        for name, private in available:
            item = QListWidgetItem(f"{name}  (private)" if private else name)
            item.setData(Qt.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if name in current else Qt.Unchecked)
            self.list.addItem(item)
        lay.addWidget(self.list, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _apply_filter(self, text):
        text = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(text) and text not in item.data(Qt.UserRole).lower())

    def selected(self):
        return [
            self.list.item(i).data(Qt.UserRole)
            for i in range(self.list.count())
            if self.list.item(i).checkState() == Qt.Checked
        ]
