import click
import os.path
from pathlib import Path

@click.group()
def cli():
    pass

@cli.command()
@click.argument('file')
@click.option('--absolute', help='Display file paths as absolute paths', is_flag=True)
@click.option('--relative-root', help='Display file paths as relative paths from root playlist', is_flag=True)
@click.option('--relative-parent', help='Display file paths as relative paths from parent playlist', is_flag=True)
@click.option('--minimal', help='Display only file names without paths', is_flag=True)
@click.option('--expand-m3u/--shrink-m3u', help='Expands/shrinks nested playlists', default=False)
@click.option('--expand-dir/--shrink-dir', help='Expands/shrinks nested directories', default=False)
def print(file, absolute, relative_root, relative_parent, minimal, expand_m3u, expand_dir):
    root = Node(Path(file))
    root.load()
    root.print(absolute, relative_root, relative_parent, expand_m3u, expand_dir)

@cli.command()
@click.argument('file')
@click.argument('export-path')
@click.option('--absolute/--relative', help='Use absolute/relative file paths (default: relative)', default=False)
@click.option('--flatten-m3u', help='Writes out nested m3u playlists', is_flag=True)
@click.option('--flatten-dir', help='Writes out nested directories', is_flag=True)
def export(file, export_path, absolute, flatten_m3u, flatten_dir):
    path = Path(export_path)

    if path.is_dir(): path = path / "playlist.m3u"
    elif path.suffix != ".m3u" or path.suffix != ".m3u8":
        path = path.with_suffix(".m3u")

    root = Node(Path(file))
    root.load()
    lines = root.export(None if absolute else path, flatten_m3u, flatten_dir)

    with open(path, 'w') as f:
        for l in lines:
            f.write(l + '\n')

class Node:
    def __init__(self, path: Path, parent_path = Path("")):
        self.children = []
        if path.exists(): self.path = path
        else: self.path = (parent_path.parent / path).resolve()
    
    def load(self, loaded_paths = []):
        if str(self.path) in loaded_paths: return
        else:
            if not self.path.exists(): pass
            elif self.getType() == "dir":
                for child_path in self.path.iterdir():
                    child = Node(child_path, self.path)
                    child.load(loaded_paths + [str(self.path)])
                    self.children.append(child)
            elif self.getType() == "m3u":
                with open(self.path) as f:
                    children_links = f.readlines()
                self.children = []
                for child_link in children_links:
                    child = Node(Path(child_link.strip()), self.path)
                    child.load(loaded_paths + [str(self.path)])
                    self.children.append(child)

    def getType(self):
        if not self.path.exists(): return "missing"
        elif self.path.is_dir(): return "dir"
        elif self.path.suffix == ".m3u" or self.path.suffix == ".m3u8": return "m3u"
        else: return "track"

    def getPath(self, absolute = False, base_path = None):
        if absolute: return self.path
        elif base_path != None and base_path.is_dir(): return Path(os.path.relpath(self.path, start=base_path))
        elif base_path != None and base_path.is_file(): return Path(os.path.relpath(self.path, start=base_path.parent))
        else: return self.path.name

    def print_children(self, prefix = "", absolute = False, relative_root = False, relative_parent = False, expand_m3u = False, expand_dir = False, root_path = None):
        for index, child in enumerate(self.children):
            connector = "└── " if index == len(self.children) - 1 else "├── "
            click.echo(prefix + connector + str(child.getPath(absolute, root_path if relative_root else self.path if relative_parent else None)))
            if (expand_m3u and child.getType() == "m3u") or (expand_dir and child.getType() == "dir"):
                extension = "    " if index == len(self.children) - 1 else "│   "
                child.print_children(prefix + extension, absolute, relative_root, relative_parent, expand_m3u, expand_dir, root_path)

    def print(self, absolute = False, relative_root = False, relative_parent = False, expand_m3u = False, expand_dir = False):
        click.echo(str(self.getPath(absolute)))
        self.print_children("", absolute, relative_root, relative_parent, expand_m3u, expand_dir, self.path)

    def export(self, base_path = None, flatten_m3u = False, flatten_dir = False, rm_duplicates = True):
        lines = []
        for child in self.children:
            if (flatten_m3u and child.getType() == "m3u") or (flatten_dir and child.getType() == "dir"):
                lines.extend(child.export(base_path, flatten_m3u, flatten_dir, rm_duplicates))
            else:
                lines.append(str(child.getPath(True if base_path == None else False, base_path)))
        return lines