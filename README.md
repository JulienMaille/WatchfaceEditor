# Watchface Editor

Toolkit for adding custom color options and hue-shifted backgrounds to Wear OS watchfaces.

## Quick Start

```powershell
# 1. Decompile, scan, generate config
.\mod_helper.ps1 -Watchface <name> -Action prepare

# 2. Edit tint_config.json, then build & sign
.\mod_helper.ps1 -Watchface <name> -Action build
```

## Config (`tint_config.json`)

| Section | Purpose |
|---|---|
| `palette` | Global color list for tint options |
| `groups` | Named groups that become ColorConfigurations in the phone app |
| `items` | Watchface elements to tint, assigned to groups |
| `hue_variants` | Generate hue-shifted PNG variants from an existing option |

Each enabled group (or standalone item) becomes a `ColorConfiguration` in the phone app with three preset options and then one per palette color:

| Option ID | Label | Effect |
|---|---|---|
| `0` | Hidden | Transparent tint (element becomes invisible) |
| `1` | Original | Element keeps its original color from the XML |
| `2+` | *(palette colors)* | Each palette entry becomes a selectable tint |

Per-group palette overrides the global one:
```json
"AOD": { "display_name": "AOD Color", "enabled": true, "palette": ["#ff88ccff", "#ff66ddaa"] }
```
This produces options: Hidden, Original, Light Blue, Blue-Green.

### Hue Variants

```json
"hue_variants": {
  "enabled": true,
  "list_config_id": "8216757e_...",
  "source_option": 6,
  "option_id_start": 10,
  "shifts": [45, 90, 135, 180, 225, 270, 315]
}
```

Generates hue-rotated PNGs from the source option's images, creates `ListOption` entries with preview icons, and registers everything in `public.xml`/`strings.xml`. Pre-made PNGs in `drawable-nodpi/` following the `_hue{deg}` naming convention skip generation.

### Complication Injection

Original complication slots are preserved. Three additional slots (101–103) are injected at predefined positions using slot 0/1 as templates. Requires `<watchface>/slots_dump.txt` from `extract_slots_full.py`.

## Files

| File | Purpose |
|---|---|
| `smart_modder.py` | Applies tint configs, injects complications, generates hue variants |
| `scan_tintable.py` | Scans watchface XML for tintable elements |
| `extract_slots_full.py` | Dumps ComplicationSlot definitions to `slots_dump.txt` |
| `mod_helper.ps1` | Automation: decompile, build, sign (release key), verify |
| `release-key.jks` | Keystore for APK signing (auto-generated if missing) |
