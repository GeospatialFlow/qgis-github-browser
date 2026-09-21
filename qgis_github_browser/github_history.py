# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later
"""
GitHub History/Diff window.

Opened from GithubDock by right-clicking a file > 'Show History / Diff'.
On the left is the list of commits that affected the file; on the right
is the change in the selected commit (unified diff, +/- lines).

Uses only the GitHub REST API (commits + the single-commit detail
endpoint, which returns the 'patch' field directly) - nothing to do with
Copilot/AI, no extra account/API key needed.
"""
import html

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QColor, QTextCharFormat
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QTextEdit, QSplitter, QPushButton,
)

from .github_api import api_get as _api_get, commit_url, commits_url
from .github_ui import warn


class GithubHistoryDialog(QDialog):
    def __init__(self, parent, repo, path, token):
        super().__init__(parent)
        self.repo = repo
        self.path = path
        self.token = token
        self.setWindowTitle(f"History: {path}")
        self.resize(900, 550)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"<b>{html.escape(repo)}</b> / {html.escape(path)}"))

        splitter = QSplitter(Qt.Horizontal)

        self.commit_list = QListWidget()
        self.commit_list.setMaximumWidth(320)
        self.commit_list.currentItemChanged.connect(self._on_select)
        splitter.addWidget(self.commit_list)

        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setFont(QFont("Consolas", 9))
        self.diff_view.setLineWrapMode(QTextEdit.NoWrap)
        splitter.addWidget(self.diff_view)
        splitter.setSizes([300, 600])

        lay.addWidget(splitter, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        row.addWidget(btn_close)
        lay.addLayout(row)

        self._load_commits()

    def _load_commits(self):
        try:
            commits = _api_get(commits_url(self.repo, self.path), self.token)
        except Exception as e:
            warn(self, "GitHub", f"Could not load history:\n{e}")
            return

        if not commits:
            self.commit_list.addItem("No commits found for this file.")
            return

        for c in commits:
            sha = c["sha"]
            msg = c["commit"]["message"].splitlines()[0]
            date = c["commit"]["author"]["date"][:10]
            author = c["commit"]["author"]["name"]
            item = QListWidgetItem(f"{date}  {msg}\n  {author} · {sha[:7]}")
            item.setData(Qt.UserRole, sha)
            self.commit_list.addItem(item)

        if self.commit_list.count():
            self.commit_list.setCurrentRow(0)

    def _on_select(self, item, _prev):
        if item is None:
            return
        sha = item.data(Qt.UserRole)
        if not sha:
            return
        self.diff_view.setPlainText("Loading...")
        try:
            detail = _api_get(commit_url(self.repo, sha), self.token)
        except Exception as e:
            self.diff_view.setPlainText(f"Error: {e}")
            return

        patch = None
        for f in detail.get("files", []):
            if f.get("filename") == self.path:
                patch = f.get("patch")
                status = f.get("status")
                break
        else:
            status = None

        if patch is None:
            if status == "renamed":
                self.diff_view.setPlainText(
                    "The file was renamed in this commit (there may be no content change)."
                )
            else:
                self.diff_view.setPlainText(
                    "Could not get a diff for this commit (the file may be too large)."
                )
            return

        self._render_diff(patch)

    def _render_diff(self, patch):
        self.diff_view.clear()
        cursor = self.diff_view.textCursor()
        fmt_add = QTextCharFormat()
        fmt_add.setForeground(QColor("#1a7f37"))
        fmt_del = QTextCharFormat()
        fmt_del.setForeground(QColor("#cf222e"))
        fmt_hunk = QTextCharFormat()
        fmt_hunk.setForeground(QColor("#8250df"))
        fmt_norm = QTextCharFormat()

        for line in patch.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                fmt = fmt_add
            elif line.startswith("-") and not line.startswith("---"):
                fmt = fmt_del
            elif line.startswith("@@"):
                fmt = fmt_hunk
            else:
                fmt = fmt_norm
            cursor.insertText(line + "\n", fmt)
