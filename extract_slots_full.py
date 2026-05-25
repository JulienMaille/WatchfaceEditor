import xml.etree.ElementTree as ET
import argparse
import os

parser = argparse.ArgumentParser(description='Extract ComplicationSlot definitions from watchface XML')
parser.add_argument('--watchface', required=True, help='Watchface name (reads from <name>/res/raw/watchface.xml)')
parser.add_argument('--output', help='Output file path (default: <watchface>/slots_dump.txt)')
args = parser.parse_args()

input_xml = os.path.join(args.watchface, 'res', 'raw', 'watchface.xml')
output_file = args.output or os.path.join(args.watchface, 'slots_dump.txt')

with open(output_file, 'w', encoding='utf-8') as out:
    try:
        tree = ET.parse(input_xml)
        root = tree.getroot()
        slots = root.findall('.//ComplicationSlot')
        for slot in slots:
            xml_str = ET.tostring(slot, encoding='unicode')
            out.write(xml_str + "\n\n")
        print(f"Dumped {len(slots)} slots to {output_file}")
    except Exception as e:
        print(f"Error: {e}")
