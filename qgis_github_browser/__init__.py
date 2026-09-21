# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later


def classFactory(iface):
    from .plugin import GithubBrowserPlugin
    return GithubBrowserPlugin(iface)
