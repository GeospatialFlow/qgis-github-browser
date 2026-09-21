# GitHub Browser - features, installation and first use

Requirements: QGIS 3.28 or newer, a GitHub account and a personal access token. Automated tests were run on QGIS 3.40 LTR (Qt5); earlier versions of the panel were also tried in QGIS 3.44. Versions below 3.40 and QGIS 4 (Qt6) are untested.

## Features

GitHub Browser is a dock panel that lets you work with GitHub repositories (private ones included) without leaving QGIS. It uses only the GitHub REST API, so no git installation is needed.

- **Browse:** repositories appear as a tree of folders and files that loads as you expand it. Several repositories can be shown at once.
- **Add repositories:** *Select Repositories...* lists every repository your token can access in a multi-select dialog with a filter, or type `owner/repo` and press *Add*. The list is remembered between sessions.
- **Remove repositories from the panel:** right-click a repository and choose *Remove repo from list*. This only hides it in the panel; nothing changes on GitHub.
- **Search:** find files by name across a whole repository in one step, then open or download them from the results.
- **Open in the Python Console:** double-click a `.py` file to open it in a Python Console editor tab. It is shown, not run.
- **Download:** save any file to disk (double-click a non-Python file, or right-click > *Download...*).
- **Upload (add or update):** *Upload Open Tab to GitHub* commits the active console tab.
  - A tab opened from GitHub can overwrite its original file directly.
  - *Save Elsewhere...* (or any tab that did not come from GitHub) opens a dialog to pick the repository, the folder at any depth (or the repository root) and the file name. Files that do not exist yet are created; if a file already exists you are asked before it is overwritten.
  - Right-click a folder > *Upload open tab here* uploads into that folder and only asks for the file name.
- **Delete:** right-click a file > *Delete...*. After a confirmation the file is removed from the repository as a commit, so it can be restored from the git history. Single files only; folders cannot be deleted from the panel.
- **History and diff:** right-click a file > *Show History / Diff* lists the commits that changed it and shows the selected change with colored added and removed lines.
- **Processing algorithm:** *Download File from GitHub* downloads one file and optionally saves it to a path. It never runs the file.
- **Token handling:** by default the token lives in memory only; optionally it is remembered encrypted in the QGIS authentication database. It is never shown again after saving and can be removed with *Forget*. See *Security* below.

Every upload and delete is an ordinary git commit in the repository.

## 1. Install

### Option A: from a ZIP (recommended)

1. Get the plugin ZIP, `qgis_github_browser-<version>.zip` (in the repository run `python scripts/build_zip.py`; the ZIP is written to `dist/`).
2. In QGIS open *Plugins > Manage and Install Plugins... > Install from ZIP*.
3. Select the ZIP file and press *Install Plugin*.
4. Open the *Installed* tab and make sure **GitHub Browser** is ticked.

### Option B: copy the folder

Copy the `qgis_github_browser` folder (the one that contains `metadata.txt`) into the plugins folder of your QGIS profile:

| System  | Folder |
|---------|--------|
| Windows | `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\` |
| Linux   | `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/` |
| macOS   | `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/` |

You can also open the profile folder from QGIS: *Settings > User Profiles > Open Active Profile Folder*, then go to `python/plugins`.

Restart QGIS and tick **GitHub Browser** in the *Installed* tab.

After installing, the plugin appears as a toolbar icon (a small tree) and under *Plugins > GitHub Browser*.

## 2. Create a GitHub token

On GitHub: *Settings > Developer settings > Personal access tokens*.

- **Classic token** with the `repo` scope: the simplest option, works for private repositories.
- **Fine-grained token**: select the repositories you want to use and give it *Contents: Read and write*.

Copy the token right away; GitHub shows it only once. Give it the least access that works: only the repositories you need and a short expiry date.

## 3. First use

1. Open the panel with the toolbar icon.
2. Paste the token and press *Save*. By default the token is kept in memory only: nothing is written to disk and it is gone when QGIS closes (use this on shared or public computers). Tick *Remember token* first if you want it kept encrypted in the QGIS authentication database; the first time, QGIS asks you to set a master password. The field is cleared after saving and the token is not shown again. *Forget* removes it.
3. Press *Select Repositories...*, tick the repositories you want and press OK. Alternatively type `owner/repo` in the *Repo* field and press *Add*. The list is remembered.
4. Expand a repository in the tree. Double-click a `.py` file to open it in a Python Console editor tab (it is not run). Double-clicking any other file asks where to save it.
5. Right-click for more:
   - file: *Open in Python console*, *Download...*, *Show History / Diff*, *Delete...*
   - folder: *Upload open tab here*
   - repository: *Remove repo from list*
6. *Upload Open Tab to GitHub* saves the active console tab as a commit. A tab opened from GitHub can overwrite its original file; otherwise a dialog lets you pick the repository, the folder (any depth) and the file name.

Use the *Search* box to find files by name across a whole repository.

## Processing algorithm

*Processing Toolbox > GitHub Browser > GitHub > Download File from GitHub* downloads a single file from a repository.

## Security

- By default the token is kept in memory only and is never written to disk. If you tick *Remember token*, it is stored in the QGIS authentication database, encrypted with your QGIS master password; it is never written to a file of this plugin or to the plain QGIS settings.
- **Shared, work or public computers:** leave *Remember token* unticked, use a token limited to one repository with a short expiry (for example one day), press *Forget* and close QGIS when you are done, and revoke the token on GitHub afterwards. Anyone who can use your unlocked session can act with your token, so lock the computer when you step away. Do not enter a token on a computer you do not trust: a keylogger sees everything you type.
- A remembered token is an encrypted entry in the QGIS authentication database, not a network credential, so a QGIS project file cannot make QGIS send it to another server.
- Every request goes to `https://api.github.com` only. The token is never sent to any other address, not even if GitHub redirects a request elsewhere.
- GitHub's TLS certificate is always verified, even if another plugin has switched certificate checking off globally.
- Dialogs show plain text, so a file or repository name coming from GitHub can never pass as HTML or a link, and the token is checked for the expected format before it is used.
- The plugin never executes downloaded code. *Open in Python console* only shows the file; pressing the console's own Run button is your decision, so run code you trust.
- Repository names and paths are validated before they are used.
- If a token may have leaked, revoke it on GitHub (*Settings > Developer settings*) and press *Forget*. Turn on two-factor authentication for your GitHub account.

## Update and uninstall

- Update: install the newer ZIP the same way; it replaces the old version.
- Uninstall: *Plugins > Manage and Install Plugins > Installed*, select **GitHub Browser** and press *Uninstall Plugin*.

## Troubleshooting

- *No token - save one above (or unlock the QGIS authentication database)*: paste the token and press *Save*, or enter your QGIS master password when asked. If you forgot the master password, reset the authentication database in *Settings > Options > Authentication* (this removes all stored QGIS credentials).
- *401/403*: the token is invalid or expired, lacks the `repo` scope (or Contents permission), or your organization requires you to authorize the token for SSO.
- *404* on a repository: the name is misspelled or the token has no access to it.
- Search finds nothing: search reads the `main` branch, so repositories with a different default branch (for example `master`) can be browsed but not searched.
- The plugin is missing after a manual copy: check that the folder contains `metadata.txt` directly (not nested one level deeper), restart QGIS, and look at the *Invalid* tab of the plugin manager.
