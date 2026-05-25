import xml.etree.ElementTree as ET
import re
import os
import copy
import json
import argparse

DEFAULT_PALETTE = [
    "#ffffffff", "#ffd0cfd1", "#ffb54cff", "#ff6cbfee",
    "#ff10b1bd", "#ff0084ae", "#ff4f87f1", "#ff779dc1",
    "#ffe58a6d", "#ffff933b", "#ffe9524b", "#ffbe0b03",
    "#ffc7db00", "#ffa1c276", "#ff4fae5d", "#ff38d21f",
    "#ffeed96c", "#fff6ee28", "#fff8ac61", "#ffe58a6d",
    "#ffaf855d"
]


def find_tint_config(path):
    for candidate in [os.path.join(path, 'tint_config.json'), 'tint_config.json']:
        if os.path.exists(candidate):
            return candidate
    return os.path.join(path, 'tint_config.json')


def find_slots_dump(path):
    for candidate in [os.path.join(path, 'slots_dump.txt'), 'slots_dump.txt']:
        if os.path.exists(candidate):
            return candidate
    return os.path.join(path, 'slots_dump.txt')


def scan_all_tintable(scene, auto_background=False):
    items = []
    wf_width = None
    wf_height = None
    root = scene
    while root is not None:
        parent = root
        root = None
    wf_elem = scene
    while wf_elem is not None and wf_elem.tag != 'WatchFace':
        wf_elem = None
    # Walk up to find WatchFace dimensions
    parent_map = {}
    for el in scene.iter():
        for child in el:
            parent_map[child] = el
    # Find width/height from WatchFace or Scene
    for el in scene.iter():
        if el.tag == 'WatchFace':
            w = el.get('width')
            h = el.get('height')
            if w and h:
                try:
                    wf_width = int(w)
                    wf_height = int(h)
                except ValueError:
                    pass
            break

    def scan(element, parent_path="Scene", depth=0):
        nonlocal wf_width, wf_height
        tag = element.tag
        name = element.get('name', '')
        current_path = f"{parent_path}/{tag}"
        if name:
            current_path += f"[{name}]"

        x = element.get('x')
        y = element.get('y')
        w = element.get('width')
        h = element.get('height')
        try:
            ex = int(x) if x else None
            ey = int(y) if y else None
            ew = int(w) if w else None
            eh = int(h) if h else None
        except ValueError:
            ex = ey = ew = eh = None

        is_fullscreen = (ex is not None and ew is not None and wf_width is not None
                         and ex <= 0 and ex + ew >= wf_width)

        tintable = tag in ('PartImage', 'PartText', 'HourHand', 'MinuteHand', 'SecondHand')

        is_bg_draw = False
        if tag == 'PartDraw':
            for child in element:
                if child.tag == 'Rectangle':
                    is_bg_draw = True
                    break

        if tintable or is_bg_draw:
            key = name if name else tag
            item = {
                "key": key,
                "tag": tag,
                "name": name if name else None,
                "path": current_path,
                "original_tintColor": element.get('tintColor'),
                "alpha": element.get('alpha'),
            }
            if auto_background:
                item["_is_fullscreen"] = is_fullscreen
            items.append(item)

        for child in element:
            scan(child, current_path, depth + 1)

    for child in scene:
        scan(child)
    return items


def is_background_name(name):
    if not name:
        return False
    lower = name.lower()
    return any(kw in lower for kw in ['bg', 'background', 'back'])


def generate_tint_config(scene, auto_background=False):
    raw_items = scan_all_tintable(scene, auto_background=auto_background)
    seen_keys = {}
    unique_items = []
    for item in raw_items:
        key = item["key"]
        if key not in seen_keys:
            seen_keys[key] = True
            unique_items.append(item)

    config = {
        "_comment": "Edit 'enabled' to false to exclude an item from tinting. Set 'group' to a shared name to group items under one config.",
        "palette": DEFAULT_PALETTE,
        "groups": {
            "Background": {
                "display_name": "Background",
                "enabled": True
            },
            "Hands": {
                "display_name": "Hands",
                "enabled": True
            },
            "Date": {
                "display_name": "Date Text",
                "enabled": True
            },
            "Bezel": {
                "display_name": "Bezel",
                "enabled": True
            }
        },
        "items": {}
    }

    for item in unique_items:
        key = item["key"]
        tag = item["tag"]

        group = None
        enabled = True

        if tag in ('HourHand', 'MinuteHand'):
            group = "Hands"
        elif tag == 'SecondHand':
            enabled = False
        elif is_background_name(key):
            group = "Background"
        elif auto_background:
            if item.get("_is_fullscreen") and tag == 'PartImage':
                group = "Background"
            elif tag == 'PartDraw':
                group = "Background"

        if 'shadow' in key.lower() or 'effect' in key.lower():
            enabled = False
        if item.get('alpha') and item['alpha'] not in ('255', None):
            try:
                if int(item['alpha']) < 50:
                    enabled = False
            except ValueError:
                pass

        config["items"][key] = {
            "tag": tag,
            "path": item["path"],
            "original_tintColor": item["original_tintColor"],
            "enabled": enabled,
            "group": group
        }

    return config


def load_or_generate_tint_config(scene, tint_config_path, auto_background=False):
    if os.path.exists(tint_config_path):
        print(f"Loading existing {tint_config_path}...")
        with open(tint_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config, False
    else:
        print(f"No {tint_config_path} found. Generating from watchface scan...")
        config = generate_tint_config(scene, auto_background=auto_background)
        os.makedirs(os.path.dirname(tint_config_path), exist_ok=True)
        with open(tint_config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"Generated {tint_config_path} with {len(config['items'])} items.")
        return config, True


def create_color_config(config_id, readable_name, string_id_prefix, strings_dict, original_tint, palette):
    config = ET.Element('ColorConfiguration')
    config.set('id', config_id)
    config.set('defaultValue', '1')

    main_string_id = f"{string_id_prefix}_title"
    strings_dict[main_string_id] = readable_name
    config.set('displayName', f"@string/{main_string_id}")
    config.set('screenReaderText', f"@string/{main_string_id}")

    hidden_opt = ET.SubElement(config, 'ColorOption')
    hidden_opt.set('id', '0')
    hidden_opt.set('colors', '#00000000')
    hidden_opt.set('displayName', "@string/hidden")
    hidden_opt.set('screenReaderText', "@string/hidden")

    default_color = '#ffffffff'
    if original_tint and isinstance(original_tint, str):
        if original_tint.startswith('#'):
            default_color = original_tint

    orig_opt = ET.SubElement(config, 'ColorOption')
    orig_opt.set('id', '1')
    orig_opt.set('colors', default_color)
    orig_opt.set('displayName', "@string/original")
    orig_opt.set('screenReaderText', "@string/original")

    for i, color in enumerate(palette):
        opt = ET.SubElement(config, 'ColorOption')
        opt.set('id', str(i + 2))
        opt.set('colors', color)
        opt.set('displayName', "ith_option_display_name")
        opt.set('screenReaderText', "ith_option_display_name")

    return config


def smart_name(component_name):
    if not component_name:
        return "Unknown"
    match = re.search(r"([a-zA-Z0-9]+)(_[a-f0-9]+)?", component_name)
    if match:
        name_part = match.group(1)
        name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name_part)
        return name
    return component_name


def write_strings_file(strings_dict, strings_xml):
    if not os.path.exists(strings_xml):
        base_dir = os.path.dirname(strings_xml)
        os.makedirs(base_dir, exist_ok=True)
        root = ET.Element('resources')
        tree = ET.ElementTree(root)
    else:
        try:
            tree = ET.parse(strings_xml)
            root = tree.getroot()
        except Exception:
            root = ET.Element('resources')
            tree = ET.ElementTree(root)

    # Derive mod name from original app_name if present
    orig_app = None
    orig_title = None
    for child in root.findall('string'):
        if child.get('name') == 'app_name':
            orig_app = child.text
        if child.get('name') == 'watchface_title':
            orig_title = child.text

    strings_dict["hidden"] = "Hidden"
    strings_dict["original"] = "Original"
    if "app_name" not in strings_dict:
        strings_dict["app_name"] = f"{orig_app} Mod" if orig_app else "Watchface Mod"
    if "watchface_title" not in strings_dict:
        strings_dict["watchface_title"] = f"{orig_title} Mod" if orig_title else "Watchface Mod"

    for name, value in strings_dict.items():
        existing = None
        for child in root.findall('string'):
            if child.get('name') == name:
                existing = child
                break
        if existing is not None:
            existing.text = value
        else:
            new_str = ET.SubElement(root, 'string')
            new_str.set('name', name)
            new_str.text = value

    if hasattr(ET, 'indent'):
        ET.indent(tree, space="    ", level=0)
    tree.write(strings_xml, encoding='UTF-8', xml_declaration=True)
    print(f"Updated {strings_xml}")


def update_manifest_package(manifest_xml, new_package_name):
    if not os.path.exists(manifest_xml):
        print(f"Warning: {manifest_xml} not found, skipping manifest update")
        return
    print(f"Updating Manifest to package: {new_package_name}")
    try:
        ET.register_namespace('android', "http://schemas.android.com/apk/res/android")
        tree = ET.parse(manifest_xml)
        root = tree.getroot()
        ns = "{http://schemas.android.com/apk/res/android}"

        for attr in ['requiredSplitTypes', 'splitTypes', 'isSplitRequired']:
            if f"{ns}{attr}" in root.attrib:
                del root.attrib[f"{ns}{attr}"]

        root.set('package', new_package_name)

        app = root.find('application')
        if app is not None:
            for attr in ['extractNativeLibs', 'isSplitRequired']:
                if f"{ns}{attr}" in app.attrib:
                    del app.attrib[f"{ns}{attr}"]
            to_remove = [m for m in app.findall('meta-data')
                         if "com.android.vending" in m.get(f"{ns}name", "")]
            for item in to_remove:
                app.remove(item)

        if hasattr(ET, 'indent'):
            ET.indent(tree, space="    ", level=0)
        tree.write(manifest_xml, encoding='UTF-8', xml_declaration=True)
        print("Manifest updated.")
    except Exception as e:
        print(f"Error updating manifest: {e}")


def load_reference_slots(slots_dump_path):
    slots = []
    try:
        with open(slots_dump_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for m in re.findall(r'(<ComplicationSlot.*?</ComplicationSlot>)', content, re.DOTALL):
            try:
                slots.append(ET.fromstring(m))
            except ET.ParseError:
                pass
    except Exception as e:
        print(f"Error loading reference slots from {slots_dump_path}: {e}")
    return slots


def inject_complex_complications(scene, slots_dump_path):
    ref_slots = load_reference_slots(slots_dump_path)
    if not ref_slots:
        print("Warning: No reference slots found.")
        return []

    template_0 = next((s for s in ref_slots if s.get('slotId') == '0'), ref_slots[0])
    template_1 = next((s for s in ref_slots if s.get('slotId') == '1'), ref_slots[0])

    created = []
    for new_id, x, y, tmpl in [(101, 80, 170, template_0),
                                 (102, 173, 260, template_1),
                                 (103, 260, 170, template_0)]:
        slot = copy.deepcopy(tmpl)
        slot.set('slotId', str(new_id))
        slot.set('displayName', f"Complication {new_id}")
        slot.set('x', str(x))
        slot.set('y', str(y))
        for elem in slot.iter():
            if 'name' in elem.attrib:
                elem.set('name', f"{elem.get('name')}_{new_id}")
        created.append(slot)

    return created


def main():
    parser = argparse.ArgumentParser(description='Watchface Color Modder')
    parser.add_argument('--watchface', help='Watchface name (e.g., ProCaptain, Bastogne). Uses subfolder as input dir.')
    parser.add_argument('--input-dir', help='Input directory containing res/raw/watchface.xml (overrides --watchface)')
    parser.add_argument('--package-name', help='New package name for the modded APK')
    parser.add_argument('--auto-background', action='store_true', help='Auto-detect background elements by position/size')
    parser.add_argument('--no-complications', action='store_true', help='Skip complication injection')
    parser.add_argument('--no-manifest', action='store_true', help='Skip manifest updates')
    parser.add_argument('--no-strings', action='store_true', help='Skip strings updates')
    parser.add_argument('--generate-only', action='store_true', help='Generate config and exit')
    args = parser.parse_args()

    if args.input_dir:
        input_dir = args.input_dir
    elif args.watchface:
        input_dir = args.watchface
    else:
        input_dir = 'source_reconstruction'

    watchface_name = args.watchface or os.path.basename(input_dir)

    input_xml = os.path.join(input_dir, 'res', 'raw', 'watchface.xml')
    output_xml = os.path.join(input_dir, 'res', 'raw', 'watchface.xml')
    strings_xml = os.path.join(input_dir, 'res', 'values', 'strings.xml')
    manifest_xml = os.path.join(input_dir, 'AndroidManifest.xml')
    tint_config_path = find_tint_config(input_dir)
    slots_dump_path = find_slots_dump(input_dir)

    if args.package_name:
        new_package_name = args.package_name
    else:
        safe_name = re.sub(r'[^a-zA-Z0-9]', '', watchface_name).lower()
        new_package_name = f"com.watchfacestudio.{safe_name}_modded"

    print(f"Input: {input_xml}")
    print(f"Config: {tint_config_path}")
    print(f"Package: {new_package_name}")

    try:
        tree = ET.parse(input_xml)
        root = tree.getroot()
    except Exception as e:
        print(f"Error reading XML: {e}")
        return

    scene = root.find('Scene')
    if scene is None:
        print("Error: No Scene element found!")
        return

    tint_config, is_new = load_or_generate_tint_config(scene, tint_config_path, auto_background=args.auto_background)

    if is_new or args.generate_only:
        print(f"\n*** {tint_config_path} has been generated. ***")
        print("Please review and edit it, then run this script again.")
        return

    palette = tint_config.get("palette", DEFAULT_PALETTE)
    groups_def = tint_config.get("groups", {})
    items_def = tint_config.get("items", {})

    user_configs = root.find('UserConfigurations')
    if user_configs is None:
        user_configs = ET.SubElement(root, 'UserConfigurations')

    existing_config_ids = set()
    list_configs = []
    color_configs = []

    for child in list(user_configs):
        cid = child.get('id', '')
        if cid:
            existing_config_ids.add(cid)
        if child.tag == 'ListConfiguration':
            list_configs.append(copy.deepcopy(child))
        elif child.tag == 'ColorConfiguration':
            color_configs.append(copy.deepcopy(child))

    for child in list(user_configs):
        user_configs.remove(child)

    for cc in color_configs:
        user_configs.append(cc)
    print(f"Preserved {len(color_configs)} existing ColorConfigurations.")

    for lc in list_configs:
        user_configs.append(lc)
    if list_configs:
        print("Preserved original ListConfiguration.")

    new_strings = {}
    created_configs = {}
    group_config_ids = {}

    for group_name, group_info in groups_def.items():
        if not group_info.get("enabled", True):
            continue
        display = group_info.get("display_name", group_name)
        safe = group_name.replace(' ', '').lower()
        config_id = f"conf_{safe}"
        if config_id in existing_config_ids:
            print(f"  Config {config_id} already exists, skipping.")
            group_config_ids[group_name] = config_id
            main_string_id = f"{config_id}_title"
            new_strings[main_string_id] = display
            continue
        cfg = create_color_config(config_id, display, config_id, new_strings, None, palette)
        user_configs.append(cfg)
        created_configs[config_id] = True
        group_config_ids[group_name] = config_id
        print(f"Created group: {display} -> {config_id}")

    applied_count = 0
    for item_key, item_info in items_def.items():
        if not item_info.get("enabled", True):
            continue

        tag = item_info.get("tag", "")
        group = item_info.get("group")
        original_tint = item_info.get("original_tintColor")

        if group and group in group_config_ids:
            config_id = group_config_ids[group]
        else:
            readable = smart_name(item_key)
            safe = readable.replace(' ', '').lower()
            config_id = f"conf_{safe}"
            if config_id not in created_configs and config_id not in existing_config_ids:
                cfg = create_color_config(config_id, readable, config_id, new_strings,
                                          original_tint, palette)
                user_configs.append(cfg)
                created_configs[config_id] = True
            else:
                main_string_id = f"{config_id}_title"
                if main_string_id not in new_strings:
                    new_strings[main_string_id] = readable

        tint_expr = f"[CONFIGURATION.{config_id}]"

        if tag in ('HourHand', 'MinuteHand'):
            for elem in root.iter(tag):
                elem.set('tintColor', tint_expr)
                applied_count += 1
        elif tag == 'SecondHand':
            pass
        else:
            for elem in root.iter():
                if elem.get('name') == item_key and elem.tag == tag:
                    elem.set('tintColor', tint_expr)
                    applied_count += 1

    print(f"Applied tint to {applied_count} items.")

    if not args.no_complications:
        for child in list(scene):
            if child.tag == 'ComplicationSlot':
                scene.remove(child)

        new_comps = inject_complex_complications(scene, slots_dump_path)

        analog_clock_idx = None
        for i, child in enumerate(scene):
            if child.tag == 'Group':
                for desc in child.iter():
                    if desc.tag in ('HourHand', 'MinuteHand', 'SecondHand', 'AnalogClock'):
                        analog_clock_idx = i
                        break
                if analog_clock_idx is not None:
                    break

        if analog_clock_idx is not None:
            for j, comp in enumerate(new_comps):
                scene.insert(analog_clock_idx + j, comp)
        else:
            for comp in new_comps:
                scene.append(comp)
    else:
        print("Complication injection skipped.")

    if not args.no_manifest:
        update_manifest_package(manifest_xml, new_package_name)

    if not args.no_strings:
        write_strings_file(new_strings, strings_xml)

    tree.write(output_xml, encoding='UTF-8', xml_declaration=True)
    print(f"Mod complete. Output: {output_xml}")

if __name__ == "__main__":
    main()
