# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later
"""
GitHub Browser (dock).

A separate panel, opened from the toolbar/menu, that lets you browse a
private GitHub repo as a tree, like a GeoPackage/PostGIS connection.
It is not added to QGIS's permanent Browser tab - it only opens when
you press the button.

Features:
- Tree-style repo browsing (folders/files, lazy-loaded)
- Search by file name (scans the whole repo tree with a single API call)
- Open a .py file in a QGIS Python Console editor tab (does not run it)
- Upload changes from the open tab back to GitHub (overwrite under the
  same name, or save as a new file under a new name)

No git installation needed, only the GitHub REST API + a token. By default
the token is kept in memory only; ticking "Remember token" stores it
encrypted in the QGIS authentication database.
"""
import os
import re
import base64
import datetime
import urllib.error

from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QInputDialog, QMenu, QAbstractItemView, QDialog,
    QCheckBox,
)

from .github_api import (
    api_get as _api_get, api_put as _api_put, api_delete as _api_delete,
    contents_url, tree_url, validate_repo,
)
from .github_auth import (
    AuthError, clear_token, get_token, has_token, save_token, set_session_token,
)
from .github_repos import fetch_user_repos, RepoPickerDialog
from .github_ui import ask, notify, warn
from .github_upload import UploadTargetDialog

REPOS_SETTING = "github_browser/repos"
REMEMBER_SETTING = "github_browser/remember"
DEFAULT_BRANCH = "main"
SAVED_HINT = "Token saved - paste a new one to replace it"

ROLE_REPO = Qt.UserRole
ROLE_PATH = Qt.UserRole + 1
ROLE_IS_DIR = Qt.UserRole + 2
ROLE_LOADED = Qt.UserRole + 3


class GithubDock(QDockWidget):
    def __init__(self, iface):
        super().__init__("GitHub Browser", iface.mainWindow())
        self.iface = iface
        self.setObjectName("GithubBrowserDock")
        self._tab_source = {}  # id(editor tab widget) -> (repo, path)

        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(4)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Token:"))
        self.ed_token = QLineEdit()
        self.ed_token.setEchoMode(QLineEdit.Password)
        self.ed_token.setPlaceholderText(
            SAVED_HINT if has_token() else "github_pat_.... or ghp_...."
        )
        row1.addWidget(self.ed_token, 1)
        self.btn_save_token = QPushButton("Save")
        self.btn_save_token.clicked.connect(self._save_token)
        row1.addWidget(self.btn_save_token)
        self.btn_forget_token = QPushButton("Forget")
        self.btn_forget_token.clicked.connect(self._forget_token)
        row1.addWidget(self.btn_forget_token)
        lay.addLayout(row1)

        self.chk_remember = QCheckBox("Remember token (encrypted, needs the QGIS master password)")
        self.chk_remember.setToolTip(
            "Leave this unticked on shared or public computers: the token then "
            "stays in memory only and is gone when QGIS is closed."
        )
        self.chk_remember.setChecked(bool(QSettings().value(REMEMBER_SETTING, False, type=bool)))
        self.chk_remember.toggled.connect(lambda on: QSettings().setValue(REMEMBER_SETTING, on))
        lay.addWidget(self.chk_remember)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Repo:"))
        self.ed_repo = QLineEdit()
        self.ed_repo.setPlaceholderText("owner/repo")
        self.ed_repo.returnPressed.connect(self._add_repo)
        row2.addWidget(self.ed_repo, 1)
        self.btn_add_repo = QPushButton("Add")
        self.btn_add_repo.clicked.connect(self._add_repo)
        row2.addWidget(self.btn_add_repo)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.populate)
        row2.addWidget(self.btn_refresh)
        lay.addLayout(row2)

        row2b = QHBoxLayout()
        self.btn_pick_repos = QPushButton("Select Repositories...")
        self.btn_pick_repos.clicked.connect(self._pick_repos)
        row2b.addWidget(self.btn_pick_repos)
        lay.addLayout(row2b)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Search:"))
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("search file/folder names...")
        self.ed_search.returnPressed.connect(self._search)
        row3.addWidget(self.ed_search, 1)
        self.btn_search = QPushButton("Search")
        self.btn_search.clicked.connect(self._search)
        row3.addWidget(self.btn_search)
        self.btn_search_clear = QPushButton("Back to Tree")
        self.btn_search_clear.clicked.connect(self._show_tree)
        self.btn_search_clear.setVisible(False)
        row3.addWidget(self.btn_search_clear)
        lay.addLayout(row3)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.itemExpanded.connect(self._on_expand)
        self.tree.itemDoubleClicked.connect(self._on_tree_double_click)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        lay.addWidget(self.tree, 1)

        self.search_list = QListWidget()
        self.search_list.itemDoubleClicked.connect(self._on_search_double_click)
        self.search_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.search_list.customContextMenuRequested.connect(self._on_search_context_menu)
        self.search_list.setVisible(False)
        lay.addWidget(self.search_list, 1)

        row4 = QHBoxLayout()
        self.btn_upload = QPushButton("Upload Open Tab to GitHub")
        self.btn_upload.clicked.connect(self._upload_current_tab)
        row4.addWidget(self.btn_upload)
        lay.addLayout(row4)

        self.setWidget(w)

        self._repos = self._load_repos()
        self.populate()

    # ------------------------------------------------------------------
    def _token(self):
        try:
            return get_token()
        except AuthError:
            return ""

    def _save_token(self):
        text = self.ed_token.text().strip()
        if not text:
            warn(self, "GitHub", "Paste a token first.")
            return
        remember = self.chk_remember.isChecked()
        try:
            if remember:
                save_token(text)
            else:
                set_session_token(text)
        except AuthError as e:
            warn(self, "GitHub", f"Could not save the token:\n{e}")
            return
        self.ed_token.clear()
        self.ed_token.setPlaceholderText(SAVED_HINT)
        if remember:
            note = "Token saved (encrypted in the QGIS authentication database)."
        else:
            note = "Token kept in memory only. It is gone when QGIS is closed."
        notify(self, "GitHub", note)
        self.populate()

    def _forget_token(self):
        if not ask(
            self, "Forget token",
            "Remove the saved token from QGIS?\nThe token itself stays valid on GitHub; "
            "revoke it there if you no longer need it.",
        ):
            return
        try:
            clear_token()
        except AuthError as e:
            warn(self, "GitHub", f"Could not remove the token:\n{e}")
            return
        self.ed_token.clear()
        self.ed_token.setPlaceholderText("github_pat_.... or ghp_....")
        self.populate()

    @staticmethod
    def _load_repos():
        value = QSettings().value(REPOS_SETTING, [])
        if isinstance(value, str):
            value = [value]
        return [r for r in (value or []) if r]

    def _save_repos(self):
        QSettings().setValue(REPOS_SETTING, self._repos)

    def _add_repo(self):
        repo = self.ed_repo.text().strip()
        if repo:
            try:
                validate_repo(repo)
            except ValueError as e:
                warn(self, "GitHub", str(e))
                return
            if repo not in self._repos:
                self._repos.append(repo)
                self._save_repos()
        self.populate()

    def _pick_repos(self):
        token = self._token()
        if not token:
            warn(self, "GitHub", "Enter a token and press Save first.")
            return
        try:
            available = fetch_user_repos(_api_get, token)
        except urllib.error.HTTPError as e:
            msg = "Token invalid or lacks permission." if e.code in (401, 403) else f"HTTP {e.code}"
            warn(self, "GitHub", f"Could not list repositories:\n{msg}")
            return
        except Exception as e:
            warn(self, "GitHub", f"Could not list repositories:\n{e}")
            return
        if not available:
            notify(self, "GitHub", "No repositories found for this token.")
            return
        dlg = RepoPickerDialog(self, available, self._repos)
        if dlg.exec_() == QDialog.Accepted:
            self._apply_repo_selection(available, dlg.selected())

    def _apply_repo_selection(self, available, selected):
        """Applies the picker result. Repos typed in by hand that the
        token cannot list are kept; listed repos follow the ticks."""
        available_names = {name for name, _ in available}
        chosen = set(selected)
        kept = [r for r in self._repos if r not in available_names or r in chosen]
        self._repos = kept + [r for r in selected if r not in kept]
        self._save_repos()
        self.populate()

    def _remove_repo(self, repo):
        if repo in self._repos:
            self._repos.remove(repo)
            self._save_repos()
        self.populate()

    def populate(self):
        self.tree.clear()
        if not self._repos:
            hint = QTreeWidgetItem(self.tree, ["Add a repository above (owner/repo)"])
            hint.setDisabled(True)
            return
        for repo in self._repos:
            root = QTreeWidgetItem(self.tree, [f"GitHub: {repo}"])
            root.setData(0, ROLE_REPO, repo)
            root.setData(0, ROLE_PATH, "")
            root.setData(0, ROLE_IS_DIR, True)
            root.setData(0, ROLE_LOADED, False)
            root.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        self.tree.expandToDepth(0)
        for i in range(self.tree.topLevelItemCount()):
            self._load_children(self.tree.topLevelItem(i))

    # ------------------------------------------------------------------
    def _on_expand(self, item):
        if not item.data(0, ROLE_LOADED):
            self._load_children(item)

    def _load_children(self, item):
        repo = item.data(0, ROLE_REPO)
        path = item.data(0, ROLE_PATH)
        item.takeChildren()
        token = self._token()
        if not token:
            err = QTreeWidgetItem(item, ["No token - save one above (or unlock the QGIS authentication database)"])
            err.setDisabled(True)
            item.setData(0, ROLE_LOADED, True)
            return
        try:
            listing = _api_get(contents_url(repo, path), token)
        except urllib.error.HTTPError as e:
            msg = (
                "401/403: token invalid or lacks permission"
                if e.code in (401, 403)
                else f"{e.code}: repo/folder not found or token cannot access this repo"
            )
            err = QTreeWidgetItem(item, [f"Error: {msg}"])
            err.setDisabled(True)
            item.setData(0, ROLE_LOADED, True)
            return
        except Exception as e:
            err = QTreeWidgetItem(item, [f"Error: {e}"])
            err.setDisabled(True)
            item.setData(0, ROLE_LOADED, True)
            return

        listing.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))
        for entry in listing:
            is_dir = entry["type"] == "dir"
            child = QTreeWidgetItem(item, [entry["name"]])
            child.setData(0, ROLE_REPO, repo)
            child.setData(0, ROLE_PATH, entry["path"])
            child.setData(0, ROLE_IS_DIR, is_dir)
            child.setData(0, ROLE_LOADED, not is_dir)
            if is_dir:
                child.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        item.setData(0, ROLE_LOADED, True)

    # ------------------------------------------------------------------
    # Search: fetches the whole repo tree in a single API call (git trees,
    # recursive) and searches the file paths - much faster than browsing
    # folder by folder.
    def _search(self):
        term = self.ed_search.text().strip().lower()
        if not term:
            return
        token = self._token()
        self.search_list.clear()
        found_any = False
        for repo in self._repos:
            try:
                data = _api_get(tree_url(repo, DEFAULT_BRANCH), token)
            except Exception as e:
                self.search_list.addItem(f"[{repo}] Error: {e}")
                continue
            for entry in data.get("tree", []):
                if entry.get("type") != "blob":
                    continue
                if term in entry["path"].lower():
                    found_any = True
                    it = QListWidgetItem(f"{repo}:  {entry['path']}")
                    it.setData(ROLE_REPO, repo)
                    it.setData(ROLE_PATH, entry["path"])
                    self.search_list.addItem(it)
        if not found_any:
            self.search_list.addItem("No results found.")
        self.tree.setVisible(False)
        self.search_list.setVisible(True)
        self.btn_search_clear.setVisible(True)

    def _show_tree(self):
        self.search_list.setVisible(False)
        self.tree.setVisible(True)
        self.btn_search_clear.setVisible(False)

    def _on_search_double_click(self, item):
        repo = item.data(ROLE_REPO)
        path = item.data(ROLE_PATH)
        if not repo or not path:
            return
        name = path.split("/")[-1]
        if path.lower().endswith(".py"):
            self._open_in_console(repo, path, name)
        else:
            self._download(repo, path, name)

    def _on_search_context_menu(self, pos):
        item = self.search_list.itemAt(pos)
        if item is None:
            return
        repo = item.data(ROLE_REPO)
        path = item.data(ROLE_PATH)
        if not repo or not path:
            return
        name = path.split("/")[-1]
        menu = QMenu(self)
        if path.lower().endswith(".py"):
            act_open = menu.addAction("Open in Python console")
            act_open.triggered.connect(lambda: self._open_in_console(repo, path, name))
        act_dl = menu.addAction("Download...")
        act_dl.triggered.connect(lambda: self._download(repo, path, name))
        act_hist = menu.addAction("Show History / Diff")
        act_hist.triggered.connect(lambda: self._show_history(repo, path))
        menu.addSeparator()
        act_del = menu.addAction("Delete...")
        act_del.triggered.connect(lambda: self._delete_file(repo, path, name))
        menu.exec_(self.search_list.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    def _on_tree_double_click(self, item, _col):
        if item.data(0, ROLE_IS_DIR):
            item.setExpanded(not item.isExpanded())
            return
        repo = item.data(0, ROLE_REPO)
        path = item.data(0, ROLE_PATH)
        name = item.text(0)
        if path.lower().endswith(".py"):
            self._open_in_console(repo, path, name)
        else:
            self._download(repo, path, name)

    def _on_tree_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if item is None:
            return
        repo = item.data(0, ROLE_REPO)
        path = item.data(0, ROLE_PATH)
        if repo is None:
            return

        if item.data(0, ROLE_IS_DIR):
            # Folder (at any depth) - option to upload the open tab here
            menu = QMenu(self)
            act_up = menu.addAction("Upload open tab here")
            act_up.triggered.connect(lambda: self._upload_current_tab_to_folder(repo, path))
            if item.parent() is None:
                menu.addSeparator()
                act_rm = menu.addAction("Remove repo from list")
                act_rm.triggered.connect(lambda: self._remove_repo(repo))
            menu.exec_(self.tree.viewport().mapToGlobal(pos))
            return

        name = item.text(0)
        menu = QMenu(self)
        if path.lower().endswith(".py"):
            act_open = menu.addAction("Open in Python console")
            act_open.triggered.connect(lambda: self._open_in_console(repo, path, name))
        act_dl = menu.addAction("Download...")
        act_dl.triggered.connect(lambda: self._download(repo, path, name))
        act_hist = menu.addAction("Show History / Diff")
        act_hist.triggered.connect(lambda: self._show_history(repo, path))
        menu.addSeparator()
        act_del = menu.addAction("Delete...")
        act_del.triggered.connect(lambda: self._delete_file(repo, path, name))
        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def _delete_file(self, repo, path, name):
        if not ask(
            self, "Delete from GitHub",
            f"Delete '{path}' from repo '{repo}'?\n"
            "This is recorded as a commit and can be reverted via git history, "
            "but the file disappears from the repo tree immediately.",
        ):
            return
        token = self._token()
        try:
            info = _api_get(contents_url(repo, path), token)
            sha = info["sha"]
        except Exception as e:
            warn(self, "GitHub", f"Could not get file info:\n{e}")
            return
        try:
            result = _api_delete(
                contents_url(repo, path), token,
                {"message": f"Deleted from QGIS: {path}", "sha": sha},
            )
            commit_sha = result.get("commit", {}).get("sha", "")[:7]
            notify(self, "GitHub", f"Deleted: {path}\nCommit: {commit_sha}")
            self.populate()
        except urllib.error.HTTPError as e:
            warn(self, "GitHub", f"Delete error ({e.code}):\n{e.read().decode('utf-8','ignore')}")
        except Exception as e:
            warn(self, "GitHub", f"Delete error:\n{e}")

    # ------------------------------------------------------------------
    def _fetch_content(self, repo, path):
        info = _api_get(contents_url(repo, path), self._token())
        return base64.b64decode(info["content"]).decode("utf-8")

    def _console_widget(self):
        import console.console as cc
        w = self.iface.mainWindow().findChild(cc.PythonConsoleWidget)
        if w is None:
            self.iface.actionShowPythonDialog().trigger()
            w = self.iface.mainWindow().findChild(cc.PythonConsoleWidget)
        return w

    def _open_in_console(self, repo, path, name):
        """Opens the content as a new tab in the QGIS Python Console editor.
        Does not run it, only displays it - the user can run it with the
        console's own Run button, or edit it and send it back with
        'Upload Open Tab to GitHub'."""
        try:
            content = self._fetch_content(repo, path)
        except Exception as e:
            warn(self, "GitHub", f"Download error:\n{e}")
            return
        try:
            import console.console_editor as ce
            w = self._console_widget()
            w.toggleEditor(True)
            tw = w.tabEditorWidget
            tw.newTabEditor()
            cur = tw.currentWidget()
            ed = cur.findChild(ce.Editor)
            ed.setText(content)
            # Do NOT call setModified(False) here: QGIS's Run button treats
            # tabs with no file path and isModified()==False as an "empty
            # script" and refuses to run them (see Editor.runScriptCode).
            # While isModified() stays True, QGIS auto-creates a temp file
            # and runs it - the only cost is that closing the tab untouched
            # may ask "save?".
            tw.setTabText(tw.indexOf(cur), name)
            self._tab_source[id(cur)] = (repo, path)
            w.show()
            w.raise_()
        except Exception as e:
            warn(self, "GitHub", f"Could not open the Python console:\n{e}")

    def _show_history(self, repo, path):
        token = self._token()
        if not token:
            warn(self, "GitHub", "Enter a token and press Save first.")
            return
        from .github_history import GithubHistoryDialog
        dlg = GithubHistoryDialog(self, repo, path, token)
        dlg.exec_()

    def _download(self, repo, path, name):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save", name)
        if not save_path:
            return
        try:
            content = self._fetch_content(repo, path)
            os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            notify(self, "GitHub", f"Saved:\n{save_path}")
        except Exception as e:
            warn(self, "GitHub", f"Download error:\n{e}")

    # ------------------------------------------------------------------
    def _get_current_tab(self):
        """Returns the active Python Console tab as (widget, tab widget,
        editor, content); shows a warning and returns None if there is
        a problem."""
        try:
            import console.console_editor as ce
        except Exception as e:
            warn(self, "GitHub", f"Python console not found:\n{e}")
            return None
        w = self._console_widget()
        if w is None:
            warn(self, "GitHub", "Could not open the Python Console.")
            return None
        tw = w.tabEditorWidget
        cur = tw.currentWidget()
        if cur is None:
            warn(self, "GitHub", "There is no open code tab.")
            return None
        ed = cur.findChild(ce.Editor)
        if ed is None:
            warn(self, "GitHub", "No code editor found in the active tab.")
            return None
        return cur, tw, ed, ed.text()

    def _do_upload(self, repo, target_path, content, cur, tw, ed, confirm_overwrite=False):
        """PUTs the given repo/path/content to GitHub - overwrites the file
        if it exists at the target (sha found), creates a new one if not
        (404). With confirm_overwrite, asks before replacing an existing
        file."""
        token = self._token()
        sha = None
        try:
            info = _api_get(contents_url(repo, target_path), token)
            sha = info.get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                warn(self, "GitHub", f"Could not get existing file info ({e.code}):\n{e.read().decode('utf-8','ignore')}")
                return
        except Exception as e:
            warn(self, "GitHub", f"Could not get existing file info:\n{e}")
            return

        if sha and confirm_overwrite:
            if not ask(
                self, "Overwrite?",
                f"'{target_path}' already exists in '{repo}'.\nOverwrite it?",
            ):
                return

        payload = {
            "message": f"Updated from QGIS: {target_path}",
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        }
        if sha:
            payload["sha"] = sha

        try:
            result = _api_put(contents_url(repo, target_path), token, payload)
            commit_sha = result.get("commit", {}).get("sha", "")[:7]
            notify(self, "GitHub", f"Uploaded: {target_path}\nCommit: {commit_sha}")
            self._tab_source[id(cur)] = (repo, target_path)
            tw.setTabText(tw.indexOf(cur), target_path.split("/")[-1])
            ed.setModified(False)
            self.populate()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            hint = ""
            if e.code == 422 and "sha" in body.lower():
                hint = "\n(A file with this name may already exist - try a different name.)"
            warn(self, "GitHub", f"Upload error ({e.code}):\n{body}{hint}")
        except Exception as e:
            warn(self, "GitHub", f"Upload error:\n{e}")

    def _upload_current_tab_to_folder(self, repo, folder_path):
        """Right-click > 'Upload open tab here' - uploads to the folder
        selected in the tree and only asks for the file name. No need to
        type a path."""
        got = self._get_current_tab()
        if got is None:
            return
        cur, tw, ed, content = got

        src = self._tab_source.get(id(cur))
        suggested_name = src[1].split("/")[-1] if src else "new_script.py"
        name, ok = QInputDialog.getText(
            self, f"Save to folder '{folder_path}/'", "File name:",
            text=suggested_name,
        )
        if not ok or not name.strip():
            return
        folder_path = folder_path.rstrip("/")
        target_path = f"{folder_path}/{name.strip()}" if folder_path else name.strip()
        self._do_upload(repo, target_path, content, cur, tw, ed)

    def _list_dirs(self, repo, path):
        listing = _api_get(contents_url(repo, path), self._token())
        return sorted((e["name"] for e in listing if e["type"] == "dir"), key=str.lower)

    @staticmethod
    def _dated_name(name):
        today = datetime.date.today().strftime("%d%m%Y")
        base, dot, ext = name.rpartition(".")
        if not dot:
            base, ext = name, ""
        base = re.sub(r"_\d{8}$", "", base)
        return f"{base}_{today}.{ext}" if ext else f"{base}_{today}"

    # Uploading back to GitHub: a tab opened from GitHub can be saved over
    # its original file straight away; anything else (or "Save Elsewhere")
    # goes through the target dialog where repo and folder are picked.
    def _upload_current_tab(self):
        got = self._get_current_tab()
        if got is None:
            return
        cur, tw, ed, content = got

        src = self._tab_source.get(id(cur))
        if src is not None:
            repo, old_path = src
            box = QMessageBox(self)
            box.setTextFormat(Qt.PlainText)
            box.setWindowTitle("Upload to GitHub")
            box.setText(f"How should '{old_path}' be saved to GitHub?")
            btn_same = box.addButton("Same Name (overwrite)", QMessageBox.AcceptRole)
            btn_new = box.addButton("Save Elsewhere...", QMessageBox.ActionRole)
            box.addButton("Cancel", QMessageBox.RejectRole)
            box.exec_()
            clicked = box.clickedButton()

            if clicked == btn_same:
                self._do_upload(repo, old_path, content, cur, tw, ed)
                return
            if clicked != btn_new:
                return
            folder, _, name = old_path.rpartition("/")
            default_repo, default_folder, default_name = repo, folder, self._dated_name(name)
        else:
            default_repo = self._repos[0] if self._repos else ""
            default_folder = ""
            default_name = self._dated_name("new_script.py")

        repos = self._repos if default_repo in self._repos else ([default_repo] if default_repo else []) + self._repos
        if not repos:
            warn(self, "GitHub", "Add a repository first (Select Repositories... or the Repo field).")
            return

        dlg = UploadTargetDialog(self, repos, self._list_dirs, default_repo, default_folder, default_name)
        if dlg.exec_() != QDialog.Accepted:
            return
        self._do_upload(dlg.repo(), dlg.target_path(), content, cur, tw, ed, confirm_overwrite=True)

    def cleanup(self):
        pass
