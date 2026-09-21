# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later
"""
Token storage. By default the token lives in memory only (nothing on disk).
If the user chooses to remember it, it goes into the QGIS authentication
database as an encrypted entry (encrypted with the QGIS master password).
It is deliberately NOT stored as a network authentication configuration:
those can be referenced by id from QGIS project files and would then be
sent to whatever server the project names.
"""
import re

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QSettings

DB_ENTRY = "github_browser/credential"
SAVED_FLAG = "github_browser/has_saved_credential"
LEGACY_SETTING = "github_browser/token"

_TOKEN_RE = re.compile(r"[A-Za-z0-9_.-]{20,255}")
_cache = {"value": ""}


class AuthError(Exception):
    pass


def _clean(token):
    token = token.strip()
    if not _TOKEN_RE.fullmatch(token):
        raise AuthError(
            "This does not look like a GitHub token (only letters, digits, "
            "'_', '-' and '.', no spaces or line breaks)."
        )
    return token


def _unlock():
    manager = QgsApplication.authManager()
    if manager.isDisabled():
        raise AuthError("The QGIS authentication system is disabled.")
    if not manager.masterPasswordIsSet() and not manager.setMasterPassword(True):
        raise AuthError("The QGIS authentication database is locked (master password not entered).")
    return manager


def has_token():
    if _cache["value"]:
        return True
    settings = QSettings()
    return bool(settings.value(SAVED_FLAG, False, type=bool) or settings.value(LEGACY_SETTING, ""))


def set_session_token(token):
    """Keeps the token in memory only: nothing is written to disk and it is
    gone when QGIS closes. Meant for shared or public computers."""
    _cache["value"] = _clean(token)


def clear_session():
    _cache["value"] = ""


def save_token(token):
    token = _clean(token)
    manager = _unlock()
    if not manager.storeAuthSetting(DB_ENTRY, token, True):
        raise AuthError("Could not store the token in the QGIS authentication database.")
    settings = QSettings()
    settings.setValue(SAVED_FLAG, True)
    settings.remove(LEGACY_SETTING)
    _cache["value"] = token


def get_token():
    """Returns the token or "" if there is none. Moves a token left in the
    plain settings by an earlier version into the authentication database.
    May ask for the QGIS master password."""
    if _cache["value"]:
        return _cache["value"]
    settings = QSettings()
    saved = settings.value(SAVED_FLAG, False, type=bool)
    legacy = settings.value(LEGACY_SETTING, "")

    found = None
    if saved:
        found = _unlock().authSetting(DB_ENTRY, None, True)
    if not found and legacy:
        save_token(legacy)
        return _cache["value"]
    if legacy:
        settings.remove(LEGACY_SETTING)
    _cache["value"] = found or ""
    return _cache["value"]


def clear_token():
    settings = QSettings()
    if settings.value(SAVED_FLAG, False, type=bool):
        _unlock().removeAuthSetting(DB_ENTRY)
    settings.remove(SAVED_FLAG)
    settings.remove(LEGACY_SETTING)
    _cache["value"] = ""
