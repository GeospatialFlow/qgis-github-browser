# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later
"""
Downloads a single file from a GitHub repo and optionally saves it to a
given local path. The file is only downloaded and shown - it is never
executed. Uses the token saved in the GitHub Browser panel.
"""
import os
import base64
import urllib.error

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterString,
    QgsProcessingException,
)

from .github_api import api_get, contents_url
from .github_auth import AuthError, get_token


class GithubDownload(QgsProcessingAlgorithm):
    REPO = "REPO"
    GITHUB_PATH = "GITHUB_PATH"
    SAVE_PATH = "SAVE_PATH"

    def tr(self, s):
        return QCoreApplication.translate("GithubDownload", s)

    def createInstance(self):
        return GithubDownload()

    def name(self):
        return "github_download"

    def displayName(self):
        return self.tr("Download File from GitHub")

    def group(self):
        return self.tr("GitHub")

    def groupId(self):
        return "github"

    def flags(self):
        # reading the token may open the QGIS master password prompt, which
        # must happen on the main thread
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def shortHelpString(self):
        return self.tr(
            "Downloads a single file from a GitHub repo.\n\n"
            "- Token: uses the token entered in the GitHub Browser panel (kept in "
            "memory, or remembered encrypted if you ticked 'Remember token').\n"
            "- GitHub Path: file path inside the repo, e.g. "
            "'scripts/tools/example.py'\n"
            "- Save Path: any full file path on your computer "
            "(if left empty the content is only printed to the log, not saved).\n\n"
            "The file is never executed. The result is printed to the log area "
            "of this window; you can also copy it from there."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterString(
                self.REPO, self.tr("Repo (user/repo-name)"),
                defaultValue="",
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.GITHUB_PATH,
                self.tr("GitHub Path (file path inside the repo)"),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.SAVE_PATH,
                self.tr("Save Path (can be left empty)"),
                optional=True,
                defaultValue="",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        repo = self.parameterAsString(parameters, self.REPO, context).strip()
        github_path = self.parameterAsString(parameters, self.GITHUB_PATH, context).strip().lstrip("/")
        save_path = self.parameterAsString(parameters, self.SAVE_PATH, context).strip()

        try:
            token = get_token()
        except AuthError as e:
            raise QgsProcessingException(str(e))
        if not token:
            raise QgsProcessingException(
                "No token saved. Open the GitHub Browser panel, paste a token and press Save."
            )
        if not github_path:
            raise QgsProcessingException("GitHub Path cannot be empty.")

        try:
            url = contents_url(repo, github_path)
        except ValueError as e:
            raise QgsProcessingException(str(e))

        feedback.pushInfo(f"Downloading: {url}")
        try:
            info = api_get(url, token)
        except urllib.error.HTTPError as e:
            raise QgsProcessingException(
                f"GitHub API error ({e.code}): {e.read().decode('utf-8', 'ignore')}"
            )

        if "content" not in info:
            raise QgsProcessingException("Could not get file content (was a folder selected?).")

        content = base64.b64decode(info["content"]).decode("utf-8")

        if save_path:
            os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            feedback.pushInfo(f"Saved: {save_path}")

        feedback.pushInfo("----- FILE CONTENT -----")
        for line in content.splitlines():
            feedback.pushInfo(line)
        feedback.pushInfo("----- END OF CONTENT -----")

        return {}
