import argparse
import json
import os
import xmltodict

args_parser = argparse.ArgumentParser(
    prog='xml2json',
    description='Convert XML to JSON'
)
args_parser.add_argument('xml_file')
args_parser.add_argument('-o', '--output', help='Output file name')

args = args_parser.parse_args()

xml_filename = os.path.splitext(args.xml_file)
base_filename = os.path.basename(xml_filename[0])

with open(args.xml_file, 'r') as f:
    data_dict = xmltodict.parse(f.read())

json_data = json.dumps(data_dict, indent=4)

with open(base_filename + ".json", "w") as f:
    f.write(json_data)