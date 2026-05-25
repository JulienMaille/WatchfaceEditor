# Watchface Editor

A toolkit for adding custom color options to Wear OS watchfaces.

## Usage

```powershell
# Step 1: Decompile APK, scan elements, generate config
.\mod_helper.ps1 -Watchface <name> -Action prepare

# Step 2: Apply mod, build APK, sign, verify
.\mod_helper.ps1 -Watchface <name> -Action build

# With release signing
.\mod_helper.ps1 -Watchface <name> -Action build -Release
```

**Step 1** extracts the watchface from `<name>.zip`, decompiles it, scans for tintable elements, and generates `tint_config.json`. Edit this file to enable/disable items and assign groups.

**Step 2** applies the tint modifications, builds the APK, zipaligns (4-byte boundary for Android 11+), and signs it.

## Configuration

`tint_config.json` (per-watchface):

```json
{
  "palette": ["#aarrggbb", ...],
  "groups": {
    "Background": { "display_name": "Background", "enabled": true }
  },
  "items": {
    "BG_46bc": {
      "tag": "PartImage",
      "path": "Scene/.../PartImage[BG_46bc]",
      "original_tintColor": null,
      "enabled": true,
      "group": "Background"
    }
  }
}
```

Each ColorConfiguration produces options: `id=0` (Hidden), `id=1` (Original), `id=2+` (palette colors).

## Tools

| Tool | Purpose |
|---|---|
| `smart_modder.py` | Applies tint/color configs and injects complications |
| `scan_tintable.py` | Scans watchface XML for tintable elements |
| `extract_slots_full.py` | Dumps ComplicationSlot definitions for injection |
| `mod_helper.ps1` | Automation: decompile, build, sign, verify |
