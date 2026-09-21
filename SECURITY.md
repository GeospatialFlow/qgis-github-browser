# Security

Only the latest release receives security fixes.

## How the plugin handles your token

- **Default: memory only.** Nothing is written to disk. The token is gone when QGIS closes, when the plugin is unloaded, or when you press *Forget*.
- **Optional: *Remember token*.** The token is stored as an encrypted entry in the QGIS authentication database, protected by your QGIS master password. It is not stored as a network authentication configuration, so a QGIS project file cannot make QGIS send it to another server. It is never written to the plain QGIS settings or to a file of this plugin.
- **Only to GitHub.** Requests go to `https://api.github.com` only. Certificates and host names are always verified, even if another plugin has switched verification off globally, and redirects to any other host are refused so the token is never forwarded.
- **Never shown again.** The token field is cleared after saving and the token is never logged or displayed. Its format is checked before it is stored or sent.
- **No code execution.** The plugin never runs downloaded code (there is no `exec` or `eval`). Opening a file only shows it in the Python Console editor; running it is your own decision.
- **Plain-text dialogs.** File names, repository names and error messages that come from GitHub are shown as plain text, so they cannot pose as HTML, links or spoofed dialogs.
- **Validated input.** Repository names and paths are validated and URL-encoded before a request is built. The plugin has no third-party dependencies.

## Limits

- Code running inside the same QGIS process (other plugins, the Python Console) can use or read the token while it is loaded or the authentication database is unlocked. Only install plugins you trust.
- Anyone who can use your unlocked QGIS session can act with your token. Lock your computer when you step away and press *Forget* when you are done.
- Nothing can protect a token you type on a computer that has a keylogger.

## Recommendations

- Use a fine-grained token limited to the repositories you need, with the least permission and a short expiry.
- On shared, work or public computers leave *Remember token* unticked, and revoke the token afterwards.
- Turn on two-factor authentication for your GitHub account.
- If a token may have leaked, revoke it on GitHub (*Settings > Developer settings*) and press *Forget*.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Write to the contact address in `qgis_github_browser/metadata.txt` and include the plugin version, your QGIS version and the steps to reproduce.
