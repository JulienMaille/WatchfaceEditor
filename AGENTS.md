# Watchface-editor — Project Guide

## Structure

| Path | Purpose |
|---|---|
| `smart_modder.py` | Core tool: reads watchface XML, applies tint/color configs, injects complications |
| `scan_tintable.py` | Scans watchface XML, lists all tintable elements, extracts palette from reference |
| `extract_slots_full.py` | Dumps ComplicationSlot definitions from a reference XML into `slots_dump.txt` |
| `mod_helper.ps1` | Automation: decompile APK, build, sign (debug or release), verify |
| `<watchface>/` | Per-watchface decompiled source + configs |
| `<watchface>/tint_config.json` | Tint configuration for that watchface (per-watchface) |
| `<watchface>/slots_dump.txt` | Complication slot definitions for injection (per-watchface) |
| `tools/apktool.jar` | APK decompiler/recompiler |
| `tools/apksigner.jar` | APK signing (from Android build-tools) |

## Workflow

```powershell
# Step 1: Decompile, scan, generate config
.\mod_helper.ps1 -Watchface <name> -Action prepare

# Step 2: Apply mod, build, sign, verify
.\mod_helper.ps1 -Watchface <name> -Action build
# Release signing
.\mod_helper.ps1 -Watchface <name> -Action build -Release
```

After step 1, edit `<watchface>/tint_config.json` — enable/disable items, set groups, change palette.

### smart_modder.py flags
- `--watchface <name>` — reads from `<name>/res/raw/watchface.xml`, uses `<name>/tint_config.json`
- `--auto-background` — auto-detect background elements by name + fullscreen position
- `--generate-only` — generate tint_config.json and exit (don't modify XML)
- `--no-complications` — skip complication injection
- `--no-manifest` — skip package name update
- `--no-strings` — skip strings.xml update

## Per-watchface files
Each watchface has its own directory with:
- `res/raw/watchface.xml` — decompiled watchface definition
- `tint_config.json` — which elements get tinted, groupings, palette
- `slots_dump.txt` — reference complication slots for injection (optional)

## Build & signing
- Debug: `apksigner` signs with built-in debug key
- Release: uses `release-key.jks` (alias: `BastogneKey`, password: `bastogne2026`)
- Pass: `.\mod_helper.ps1 -Watchface X -Action build -Release`

## Color schema
Colors in `#AARRGGBB` format. Palette in `tint_config.json`. Each ColorConfiguration gets:
- `id=0` — Hidden (transparent)
- `id=1` — Original (element's original color or white)
- `id=2+` — One per palette color
