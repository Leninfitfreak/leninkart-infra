import os
import argparse

def dump_project_to_file(root_dir='.', output_file='project_dump.txt', ignore_dirs=None, ignore_files=None):
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__pycache__', '.idea', '.vscode', 'node_modules', 'build', 'dist', '.gradle'}
    if ignore_files is None:
        ignore_files = {'.DS_Store', 'Thumbs.db'}

    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write(f"# Project Dump - Root: {os.path.abspath(root_dir)}\n\n")

        for current_dir, dirs, files in os.walk(root_dir):
            # Skip ignored directories (in-place modification)
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            relative_dir = os.path.relpath(current_dir, root_dir)
            if relative_dir != '.':
                outfile.write(f"### DIRECTORY: {relative_dir}/\n\n")

            for file_name in sorted(files):
                if file_name in ignore_files:
                    continue

                file_path = os.path.join(current_dir, file_name)
                relative_path = os.path.relpath(file_path, root_dir)

                outfile.write(f"### FILE: {relative_path}\n")
                outfile.write("```\n")

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    outfile.write(content.rstrip() + "\n")  # Ensure trailing newline
                except UnicodeDecodeError:
                    outfile.write("<BINARY OR NON-UTF8 FILE - CONTENT SKIPPED>\n")
                except PermissionError:
                    outfile.write("<PERMISSION DENIED - CONTENT SKIPPED>\n")
                except Exception as e:
                    outfile.write(f"<ERROR READING FILE: {str(e)}>\n")

                outfile.write("```\n\n")

    print(f"Project dump completed! File saved as '{output_file}' in the current directory.")
    print("Share the content of this file with me — I'll analyze every line and fix LeninKart!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dump entire project file structure and content to a single text file")
    parser.add_argument('-o', '--output', default='project_dump.txt', help='Output file name (default: project_dump.txt)')
    parser.add_argument('-r', '--root', default='.', help='Root directory to scan (default: current directory)')

    args = parser.parse_args()

    dump_project_to_file(root_dir=args.root, output_file=args.output)