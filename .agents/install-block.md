Run from the repository root after installing the Python CLI.

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\link-skills.ps1
```

macOS or Linux:

```bash
bash scripts/link-skills.sh
```

The scripts link skills into both `~/.codex/skills` (or `$CODEX_HOME/skills` when configured) and `~/.agents/skills`. Re-running them keeps existing links and refuses to overwrite a conflicting installation. Links follow this checkout, so `git pull` updates installed skill content. Re-run after adding, removing, or renaming a skill. Start a new turn after installation to load the skill.

The repository also includes a single-plugin marketplace in `.Codex-plugin/marketplace.json` as a fallback for plugin-aware clients; the local linking commands above are the documented installation route.
