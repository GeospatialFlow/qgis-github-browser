# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later
import os

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .github_download import GithubDownload


class GithubBrowserProvider(QgsProcessingProvider):
    def id(self):
        return "github_browser"

    def name(self):
        return "GitHub Browser"

    def longName(self):
        return self.name()

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.png"))

    def loadAlgorithms(self):
        self.addAlgorithm(GithubDownload())
