# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later
"""
Upload target dialog: pick the repository from a drop-down, pick the
folder in a lazily loaded folder tree (any depth, or the repo root) and
type the file name. Nothing has to be typed as a path.
"""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QTreeWidget, QTreeWidgetItem, QDialogButtonBox,
)

ROLE_PATH = Qt.UserRole
ROLE_LOADED = Qt.UserRole + 1


class UploadTargetDialog(QDialog):
    def __init__(self, parent, repos, list_dirs, default_repo, default_folder, default_name):
        """list_dirs(repo, path) -> sorted folder names directly under path."""
        super().__init__(parent)
        self.setWindowTitle("Upload to GitHub")
        self.resize(440, 520)
        self._list_dirs = list_dirs
        self._default_folder = default_folder

        lay = QVBoxLayout(self)

        row = QHBoxLayout()
        row.addWidget(QLabel("Repo:"))
        self.cb_repo = QComboBox()
        self.cb_repo.addItems(repos)
        row.addWidget(self.cb_repo, 1)
        lay.addLayout(row)

        lay.addWidget(QLabel("Folder (select where the file goes):"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemExpanded.connect(self._on_expand)
        self.tree.itemSelectionChanged.connect(self._update_target)
        lay.addWidget(self.tree, 1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("File name:"))
        self.ed_name = QLineEdit(default_name)
        self.ed_name.textChanged.connect(self._update_target)
        row2.addWidget(self.ed_name, 1)
        lay.addLayout(row2)

        self.lbl_target = QLabel()
        self.lbl_target.setTextFormat(Qt.PlainText)
        self.lbl_target.setWordWrap(True)
        lay.addWidget(self.lbl_target)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Upload")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)

        if default_repo in repos:
            self.cb_repo.setCurrentText(default_repo)
        self.cb_repo.currentTextChanged.connect(self._load_root)
        self._load_root()

    def _load_root(self, *_):
        self.tree.clear()
        root = QTreeWidgetItem(self.tree, ["(repo root)"])
        root.setData(0, ROLE_PATH, "")
        root.setData(0, ROLE_LOADED, False)
        self._load_children(root)
        root.setExpanded(True)
        target = self._select_folder(self._default_folder)
        self._default_folder = ""
        self.tree.setCurrentItem(target)
        self._update_target()

    def _load_children(self, item):
        item.takeChildren()
        path = item.data(0, ROLE_PATH)
        try:
            names = self._list_dirs(self.cb_repo.currentText(), path)
        except Exception as e:
            err = QTreeWidgetItem(item, [f"Error: {e}"])
            err.setDisabled(True)
            item.setData(0, ROLE_LOADED, True)
            return
        for name in names:
            child = QTreeWidgetItem(item, [name])
            child.setData(0, ROLE_PATH, f"{path}/{name}" if path else name)
            child.setData(0, ROLE_LOADED, False)
            child.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        item.setData(0, ROLE_LOADED, True)

    def _on_expand(self, item):
        if not item.data(0, ROLE_LOADED):
            self._load_children(item)
            if item.childCount() == 0:
                item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicator)

    def _select_folder(self, path):
        """Expands down to `path` and returns the deepest folder found
        (the repo root if the path is empty or does not exist)."""
        item = self.tree.topLevelItem(0)
        for seg in [p for p in path.split("/") if p]:
            if not item.data(0, ROLE_LOADED):
                self._load_children(item)
            match = None
            for i in range(item.childCount()):
                if item.child(i).text(0) == seg:
                    match = item.child(i)
                    break
            if match is None:
                break
            item.setExpanded(True)
            item = match
        return item

    def repo(self):
        return self.cb_repo.currentText()

    def folder(self):
        item = self.tree.currentItem()
        path = item.data(0, ROLE_PATH) if item is not None else None
        return path or ""

    def target_path(self):
        name = self.ed_name.text().strip()
        folder = self.folder()
        return f"{folder}/{name}" if folder else name

    def _update_target(self, *_):
        name = self.ed_name.text().strip()
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(bool(name))
        self.lbl_target.setText(
            f"Target: {self.repo()}/{self.target_path()}" if name else "Enter a file name."
        )
