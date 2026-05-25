import xml.etree.ElementTree as ET
import json
import os
import argparse

parser = argparse.ArgumentParser(description='Scan watchface XML for tintable elements')
parser.add_argument('--watchface', help='Watchface name (e.g., MyWatchface). Uses subfolder as input.')
parser.add_argument('--ref-dir', help='Reference mod directory (to extract palette)')
parser.add_argument('--orig-dir', help='Original/decompiled watchface directory (to scan)')
parser.add_argument('--output', help='Output JSON file path (default: <watchface-dir>/tintable_scan.json)')
args = parser.parse_args()

if args.orig_dir:
    orig_dir = args.orig_dir
elif args.watchface:
    orig_dir = args.watchface
else:
    orig_dir = 'source_original'

if args.ref_dir:
    ref_dir = args.ref_dir
else:
    ref_dir = orig_dir

ref_xml = os.path.join(ref_dir, 'res', 'raw', 'watchface.xml')
orig_xml = os.path.join(orig_dir, 'res', 'raw', 'watchface.xml')
output_file = args.output or os.path.join(orig_dir, 'tintable_scan.json')

# 1. Extract reference color palette (if reference has ColorConfigurations)
palette = []
print(f"Reading reference: {ref_xml}")
try:
    ref_tree = ET.parse(ref_xml)
    ref_root = ref_tree.getroot()
    ref_uc = ref_root.find('UserConfigurations')
    if ref_uc is not None:
        for config in ref_uc:
            if config.tag == 'ColorConfiguration':
                colors = []
                for opt in config:
                    if opt.tag == 'ColorOption':
                        colors.append(opt.get('colors', ''))
                if colors:
                    palette = colors
                    config_name = config.get('displayName', '')
                    config_id = config.get('id', '')
                    print(f"  Config '{config_name}' (id={config_id}): {len(colors)} colors")
                    break
except FileNotFoundError:
    print(f"  No reference XML found at {ref_xml}, using default palette")

if not palette:
    palette = [
        "#ffffffff", "#ffd0cfd1", "#ffb54cff", "#ff6cbfee",
        "#ff10b1bd", "#ff0084ae", "#ff4f87f1", "#ff779dc1",
        "#ffe58a6d", "#ffff933b", "#ffe9524b", "#ffbe0b03",
        "#ffc7db00", "#ffa1c276", "#ff4fae5d", "#ff38d21f",
        "#ffeed96c", "#fff6ee28", "#fff8ac61", "#ffe58a6d",
        "#ffaf855d"
    ]

print(f"\nPalette ({len(palette)} colors):")
for i, c in enumerate(palette):
    print(f"  [{i}] {c}")

# 2. Scan original for ALL tintable elements
print(f"\nReading original: {orig_xml}")
orig_tree = ET.parse(orig_xml)
orig_root = orig_tree.getroot()
orig_scene = orig_root.find('Scene')

tintable_items = []

def scan_element(element, parent_path="Scene"):
    tag = element.tag
    name = element.get('name', '')
    current_path = f"{parent_path}/{tag}"
    if name:
        current_path += f"[{name}]"

    tint = element.get('tintColor', None)
    alpha = element.get('alpha', None)
    resource = element.get('resource', None)

    is_background = False
    if tag == 'PartDraw':
        for child in element:
            if child.tag == 'Rectangle':
                is_background = True
                break

    if tag in ('PartImage', 'PartText', 'HourHand', 'MinuteHand', 'SecondHand') or is_background:
        item = {
            "tag": tag,
            "name": name if name else None,
            "path": current_path,
            "original_tintColor": tint,
            "alpha": alpha,
            "resource": resource[:50] + "..." if resource and len(resource) > 50 else resource,
        }
        tintable_items.append(item)
        print(f"  {current_path}")
        print(f"    tintColor={tint} alpha={alpha}")

    for child in element:
        scan_element(child, current_path)

for child in orig_scene:
    scan_element(child)

print(f"\nTotal tintable items: {len(tintable_items)}")

output = {
    "palette": palette,
    "items": tintable_items,
}
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f"Saved to {output_file}")
