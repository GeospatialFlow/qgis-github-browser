# qgis-github-browser

A QGIS plugin: browse, open, edit and upload files in GitHub repositories from within QGIS.

## Features

- Browse repositories (including private ones) as a lazy-loaded tree in a dock panel
- Search file names across a whole repository with a single API call
- Open a `.py` file in a Python Console editor tab (it is not run)
- Upload the open tab back to GitHub as a commit: overwrite the original file, or pick the repository, folder (any depth) and file name in a dialog; you can also right-click a folder and upload there
- Per-file commit history with a colored diff
- Delete a file from GitHub (recorded as a commit)
- Processing algorithm: download a single file from a repository (never executed)
- Uses only the GitHub REST API - no git installation needed

## Install

Build the ZIP and install it via *Plugins > Manage and Install Plugins > Install from ZIP*:

```
python scripts/build_zip.py
```

The ZIP is written to `dist/`. Automated tests were run on QGIS 3.40 LTR (Qt5); earlier versions of the panel were also tried in QGIS 3.44. Versions below 3.40 and QGIS 4 (Qt6) are untested. Full steps, token setup and troubleshooting: [qgis_github_browser/INSTALL.md](qgis_github_browser/INSTALL.md).

## Token

Create a GitHub personal access token (a fine-grained token limited to the repositories you need is safest; a classic token with the `repo` scope is the simplest), paste it into the panel and press Save. By default the token is kept in memory only, so nothing is written to disk and it is gone when QGIS closes; this is the setting for shared or public computers. Tick *Remember token* to keep it encrypted in the QGIS authentication database instead (QGIS asks for a master password the first time). It is never written to a file in this repository or to the plain QGIS settings. *Forget* removes it.

## Security

- The token is kept in memory only by default. Ticking *Remember token* stores it as an encrypted entry in the QGIS authentication database (not as a network credential that project files could reference).
- The token goes only to `https://api.github.com`, over HTTPS with certificate verification that other plugins cannot switch off, never to any other address, not even after a redirect.
- Downloaded code is never executed by the plugin, and dialogs show plain text so names coming from GitHub cannot pose as HTML or links.
- Repository names, paths and the token format are validated before use.
- On shared, work or public computers leave *Remember token* unticked, use a short-lived token limited to one repository, and revoke it afterwards.

See [SECURITY.md](SECURITY.md) for details, limits and how to report a vulnerability.

## Repositories

Press *Select Repositories...* to pick from every repository your token can access (private ones included), or type a repository as `owner/repo` and press Add. The list is remembered between sessions; right-click a repository in the tree to remove it.

## License

GPL-2.0-or-later - see [LICENSE](LICENSE).
