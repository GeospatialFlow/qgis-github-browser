# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Builds dist/qgis_github_browser-<version>.zip, ready for
Plugins > Manage and Install Plugins > Install from ZIP."""
import configparser
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = "qgis_github_browser"

cfg = configparser.ConfigParser()
cfg.read(os.path.join(ROOT, PKG, "metadata.txt"), encoding="utf-8")
version = cfg["general"]["version"]

os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
out = os.path.join(ROOT, "dist", f"{PKG}-{version}.zip")

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for folder, dirs, files in os.walk(os.path.join(ROOT, PKG)):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if name.endswith(".pyc"):
                continue
            full = os.path.join(folder, name)
            z.write(full, os.path.relpath(full, ROOT))

print(out)
