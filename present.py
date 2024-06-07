import argparse, json
from pathlib import Path

def get_args():
    parser = argparse.ArgumentParser(description='Gather commits and issues from GitHub repositories')
    parser.add_argument('-i', '--input', help='Path to the input file', type=str, required=True)
    parser.add_argument('-m', '--milestone', type=int, help='Milestone number', required=True)
    return parser.parse_args()

def main():
    args = get_args()

    input_file = Path(args.input)
    with input_file.open() as f:
        data = json.load(f)
    
    ms = data[args.milestone - 1]

    input_file_stem = input_file.stem
    output_file = input_file.with_name(f'{input_file_stem}-milestone-{args.milestone}.json')

    with output_file.open('w') as f:
        json.dump(ms, f, ensure_ascii=False, indent=4)
    
    print(f'Milestone {args.milestone} saved to {output_file}')

if __name__ == '__main__':
    main()