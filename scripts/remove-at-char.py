import json
import argparse
from pathlib import Path


def remove_at_symbols(data):
    """
    Recursively remove @ symbols from dictionary keys.

    Args:
        data: Dictionary, list, or primitive value

    Returns:
        Modified data with @ symbols removed from keys
    """
    if isinstance(data, dict):
        return {
            key.lstrip('@'): remove_at_symbols(value)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [remove_at_symbols(item) for item in data]
    else:
        return data


def clean_json_file(input_file, output_file=None):
    """
    Remove @ symbols from JSON file keys.

    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file (optional, will append '_clean' if not provided)
    """
    input_path = Path(input_file)

    # Generate output filename if not provided
    if output_file is None:
        output_path = input_path.parent / f"{input_path.stem}_clean{input_path.suffix}"
    else:
        output_path = Path(output_file)

    # Read input JSON
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Remove @ symbols
    cleaned_data = remove_at_symbols(data)

    # Write output JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Cleaned JSON written to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Remove @ symbols from JSON keys',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clean_json.py input.json
  python clean_json.py input.json -o output.json
        """
    )

    parser.add_argument(
        'input',
        type=str,
        help='Input JSON file path'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output JSON file path (default: input_clean.json)'
    )

    args = parser.parse_args()

    try:
        clean_json_file(args.input, args.output)
    except FileNotFoundError:
        print(f"Error: File not found: {args.input}")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == '__main__':
    main()