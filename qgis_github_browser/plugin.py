# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later
import os

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .github_auth import clear_session
from .processing_provider import GithubBrowserProvider

MENU = "&GitHub Browser"


class GithubBrowserPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.action = None
        self.dock = None

    def initGui(self):
        self.provider = GithubBrowserProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        icon = QIcon(os.path.join(os.path.dirname(__file__), "icon.png"))
        self.action = QAction(icon, "GitHub Browser", self.iface.mainWindow())
        self.action.triggered.connect(self.show_dock)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(MENU, self.action)

    def show_dock(self):
        try:
            if self.dock is None:
                from .github_dock import GithubDock
                self.dock = GithubDock(self.iface)
                self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
            self.dock.show()
            self.dock.raise_()
        except Exception as e:
            self.iface.messageBar().pushWarning("GitHub Browser", f"Could not open the panel: {e}")

    def unload(self):
        clear_session()
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        if self.action is not None:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu(MENU, self.action)
            self.action = None
        if self.dock is not None:
            self.dock.cleanup()
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
