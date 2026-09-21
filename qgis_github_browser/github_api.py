# -*- coding: utf-8 -*-
# Copyright (C) 2026 The qgis-github-browser authors
# SPDX-License-Identifier: GPL-2.0-or-later
"""
The only place that talks to the network. Every request goes to
https://api.github.com over HTTPS; the token is never sent anywhere else,
not even after a redirect. Repository names and paths are validated and
URL-encoded before a URL is built.
"""
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

API_HOST = "api.github.com"
API_ROOT = f"https://{API_HOST}"
TIMEOUT = 30

_OWNER_RE = re.compile(r"[A-Za-z0-9_-]+")
_NAME_RE = re.compile(r"[A-Za-z0-9_.-]+")
_SHA_RE = re.compile(r"[0-9a-fA-F]{7,64}")


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    """urllib forwards the Authorization header on redirects. Only follow a
    redirect if it stays on the GitHub API host."""

    def __init__(self, host=API_HOST, scheme="https"):
        self._host = host
        self._scheme = scheme

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if target.scheme != self._scheme or target.hostname != self._host:
            raise urllib.error.HTTPError(
                req.full_url, code, "Redirect to another host blocked", headers, fp
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# Own TLS context: certificate and host name are always verified, even if
# another plugin switched verification off globally
# (ssl._create_default_https_context = ssl._create_unverified_context).
_TLS = ssl.create_default_context()
_TLS.minimum_version = ssl.TLSVersion.TLSv1_2

_opener = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=_TLS),
    _SameHostRedirect(),
)


def validate_repo(repo):
    owner, sep, name = repo.partition("/")
    if (not sep or "/" in name or not _OWNER_RE.fullmatch(owner)
            or not _NAME_RE.fullmatch(name) or name in (".", "..")):
        raise ValueError(f"Invalid repository '{repo}' (expected owner/repo)")
    return repo


def quote_path(path):
    segments = [s for s in path.split("/") if s]
    if any(s in (".", "..") for s in segments):
        raise ValueError(f"Invalid path '{path}'")
    return "/".join(urllib.parse.quote(s, safe="") for s in segments)


def contents_url(repo, path=""):
    return f"{API_ROOT}/repos/{validate_repo(repo)}/contents/{quote_path(path)}"


def tree_url(repo, branch):
    return (f"{API_ROOT}/repos/{validate_repo(repo)}/git/trees/"
            f"{urllib.parse.quote(branch, safe='')}?recursive=1")


def commits_url(repo, path):
    return (f"{API_ROOT}/repos/{validate_repo(repo)}/commits"
            f"?path={urllib.parse.quote(path, safe='/')}&per_page=100")


def commit_url(repo, sha):
    if not _SHA_RE.fullmatch(sha):
        raise ValueError("Invalid commit id")
    return f"{API_ROOT}/repos/{validate_repo(repo)}/commits/{sha}"


def _request(method, url, token, payload=None):
    target = urllib.parse.urlsplit(url)
    if target.scheme != "https" or target.hostname != API_HOST:
        raise ValueError(f"Refusing to send the token to {target.hostname}")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with _opener.open(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_get(url, token):
    return _request("GET", url, token)


def api_put(url, token, payload):
    return _request("PUT", url, token, payload)


def api_delete(url, token, payload):
    return _request("DELETE", url, token, payload)
