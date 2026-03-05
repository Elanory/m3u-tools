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
@click.option('--expand-playlist/--shrink-playlist', help='Expands/shrinks nested playlists', default=False)
@click.option('--expand-dir/--shrink-dir', help='Expands/shrinks nested directories', default=False)
@click.option('--display-empty', help='Display empty lines in playlist', is_flag=True)
@click.option('--display-comment', help='Display comments in playlist', is_flag=True)
@click.option('--display-extinf', help='Display ExtInf in playlist', is_flag=True)
def print(file, absolute, relative_root, relative_parent, expand_playlist, expand_dir, display_empty, display_comment, display_extinf):
    root = M3UEntry(file)
    if isinstance(root, Playlist):
        root._load()
        click.echo(root.print())
        entries = root.printChildren(absolute=absolute, relative_root=relative_root, relative_parent=relative_parent, expand_playlist=expand_playlist, expand_dir=expand_dir, empty=display_empty, comment=display_comment, extinf=display_extinf, root=root.path)
        print_recursive(entries)

def print_recursive(entries, prefix = ""):
    for index, entry in enumerate(entries):
        is_last = True
        for e in entries[index + 1:]:
            if not isinstance(e, list): is_last = False

        if isinstance(entry, list):
            extension = "    " if is_last else "│   "
            print_recursive(entry, prefix + extension)
        else:
            connector = "└── " if is_last else "├── "
            click.echo(prefix + connector + entry)

@cli.command()
@click.argument('file')
@click.argument('export-path')
@click.option('--absolute/--relative', help='Use absolute/relative file paths (default: relative)', default=False)
@click.option('--flatten-playlist', help='Writes out nested playlists', is_flag=True)
@click.option('--flatten-dir', help='Writes out nested directories', is_flag=True)
@click.option('--remove-empty', help='Remove empty lines', is_flag=True)
@click.option('--remove-comment', help='Remove comments', is_flag=True)
@click.option('--remove-extinf', help='Remove EXTINF', is_flag=True)
def export(file, export_path, absolute, flatten_playlist, flatten_dir, remove_empty, remove_comment, remove_extinf):
    path = Path(export_path)

    if path.suffix not in (".m3u", ".m3u8"):
        click.echo("Error: export path must have extension '.m3u' or '.m3u8'")
        return

    root = M3UEntry(file)
    if isinstance(root, Playlist) or isinstance(root, Folder):
        root._load()
        lines = flatten(root.printChildren(absolute, relative_root = not absolute, relative_parent = False, expand_playlist = flatten_playlist, playlist_header=not flatten_playlist, expand_dir = flatten_dir, dir_header=not flatten_dir, empty = not remove_empty, comment = not remove_comment, extinf = not remove_extinf, root = Path(export_path)))

        with open(path, 'w') as f:
            for l in lines:
                f.write(l + '\n')

def flatten(entries):
    output = []
    for entry in entries:
        if isinstance(entry, list):
            output.extend(flatten(entry))
        else:
            output.append(entry)
    return output

class M3UEntry:
    def __new__(cls, line, parent: Path = Path("")):
        if isinstance(line, str):
            line = line.strip()

            if cls is M3UEntry:
                if not line:
                    return super().__new__(Comment)

                elif line.startswith("#EXTM3U"):
                    return super().__new__(PlaylistDirective)

                elif line.startswith("#EXTINF:"):
                    return super().__new__(ExtInf)

                elif line.startswith("#"):
                    return super().__new__(Comment)

                elif line.endswith(".m3u") or line.endswith(".m3u8"):
                    return super().__new__(Playlist)
                
                elif line.endswith("/") or line.endswith("\\"):
                    return super().__new__(Folder)
                
                else:
                    return super().__new__(Track)
                
            else:
                return super().__new__(cls)
            
        elif isinstance(line, Path):
            if cls is M3UEntry:
                if line.is_file() and line.suffix in [".m3u", ".m3u8"]:
                    return super().__new__(Playlist)
                elif line.is_dir():
                    return super().__new__(Folder)
                else:
                    return super().__new__(Track)
                
            else:
                return super().__new__(cls)
            
        else:
            raise TypeError(f"Unsupported type {type(line)}")

    def __init__(self, line: str):
        self.raw = str(line).strip()

class Comment(M3UEntry):
    def __init__(self, line: str, parent: Path = Path("")):
        super().__init__(line)
        self.text = self.raw.lstrip("#").strip()

    def __repr__(self):
        return f"<Comment: {self.text}>"
    
    def print(self):
        if not self.text: return ""
        else: return f"# {self.text}"

class PlaylistDirective(M3UEntry):
    def __init__(self, line: str, parent: Path = Path("")):
        super().__init__(line)

    def __repr__(self):
        return f"<PlaylistDirective>"
    
    def print(self):
        return "#EXTM3U"

class Playlist(M3UEntry):
    def __init__(self, line, parent: Path = Path("")):
        super().__init__(line)

        if isinstance(line, str):
            self.path = Path(self.raw)
        elif isinstance(line, Path):
            self.path = line

        if not self.path.is_absolute():
            self.path = (parent.parent / self.path).resolve()
            
        self.entries = []

    def _parse(self, lines):
        pending_extinf = None

        for line in lines:
            entry = M3UEntry(line, self.path)

            if isinstance(entry, ExtInf):
                pending_extinf = entry
                continue

            if isinstance(entry, Track) and pending_extinf:
                entry.attach_extinf(pending_extinf)
                pending_extinf = None

            self.entries.append(entry)

    def _load(self):
        if self.path.is_file():
            self.entries = []

            with open(self.path) as f:
                lines = f.readlines()
            self._parse(lines)

            for entry in self.entries:
                if isinstance(entry, Playlist) or isinstance(entry, Folder):
                    entry._load()

    def printChildren(self, absolute = False, relative_root = False, relative_parent = False, expand_playlist = False, playlist_header = True, expand_dir = False, dir_header = True, empty = False, comment = False, extinf = False, root = None):
        output = []
        
        for entry in self.entries:
            if isinstance(entry, Comment):
                if comment:
                    if entry.print() or empty:
                        output.append(entry.print())

            elif isinstance(entry, PlaylistDirective):
                if extinf:
                    output.append(entry.print())

            elif isinstance(entry, Folder):
                if dir_header:
                    output.append(entry.print(absolute, (root if relative_root else self.path if relative_parent else None)))
                else:
                    if empty: output.append("")
                    if comment: output.append(f"# {entry.print(False, None)}")

                if(expand_dir):
                    output.append(entry.printChildren(absolute, relative_root, relative_parent, expand_playlist, playlist_header, expand_dir, dir_header, empty, comment, extinf, root))
                    if empty: output.append("")
            
            elif isinstance(entry, Playlist):
                if playlist_header:
                    output.append(entry.print(absolute, (root if relative_root else self.path if relative_parent else None)))
                else:
                    if empty: output.append("")
                    if comment: output.append(f"# {entry.print(False, None)}")

                if(expand_playlist):
                    output.append(entry.printChildren(absolute, relative_root, relative_parent, expand_playlist, playlist_header, expand_dir, dir_header, empty, comment, extinf, root))
                    if empty: output.append("")
            
            elif isinstance(entry, Track):
                if extinf and entry.printExtInf():
                    output.append(entry.printExtInf())
                output.append(entry.print(absolute, (root if relative_root else self.path if relative_parent else None)))

        return output

    def __repr__(self):
        return f"<Playlist: {self.path}>"

    def print(self, absolute = False, base: Path = None):
        if absolute:
            return str(self.path)
        elif base:
            if base.is_dir():
                return os.path.relpath(self.path, start = base)
            else:
                return os.path.relpath(self.path, start = base.parent)
        else: 
            return str(self.path.name)
        
class Folder(M3UEntry):
    def __init__(self, line, parent: Path = Path("")):
        super().__init__(line)

        if isinstance(line, str):
            self.path = Path(self.raw)
        elif isinstance(line, Path):
            self.path = line
            
        if not self.path.is_absolute():
            self.path = (parent.parent / self.path).resolve()

        self.entries = []

    def _load(self):
        if self.path.is_dir():
            self.entries = []

            for path in self.path.iterdir():
                entry = M3UEntry(path)
                self.entries.append(entry)

            for entry in self.entries:
                if isinstance(entry, Playlist) or isinstance(entry, Folder):
                    entry._load()

    def printChildren(self, absolute = False, relative_root = False, relative_parent = False, expand_playlist = False, playlist_header = True, expand_dir = False, dir_header = True, empty = False, comment = False, extinf = False, root = None):
        output = []
        
        for entry in self.entries:
            if isinstance(entry, Folder):
                if dir_header:
                    output.append(entry.print(absolute, (root if relative_root else self.path if relative_parent else None)))
                else:
                    if empty: output.append("")
                    if comment: output.append(f"# {entry.print(False, None)}")

                if(expand_dir):
                    output.append(entry.printChildren(absolute, relative_root, relative_parent, expand_playlist, playlist_header, expand_dir, dir_header, empty, comment, extinf, root))
                    if empty: output.append("")
            
            elif isinstance(entry, Playlist):
                if playlist_header:
                    output.append(entry.print(absolute, (root if relative_root else self.path if relative_parent else None)))
                else:
                    if empty: output.append("")
                    if comment: output.append(f"# {entry.print(False, None)}")

                if(expand_playlist):
                    output.append(entry.printChildren(absolute, relative_root, relative_parent, expand_playlist, playlist_header, expand_dir, dir_header, empty, comment, extinf, root))
                    if empty: output.append("")
            
            elif isinstance(entry, Track):
                output.append(entry.print(absolute, (root if relative_root else self.path if relative_parent else None)))

        return output

    def __repr__(self):
        return f"<Folder: {self.path}>"

    def print(self, absolute = False, base: Path = None):
        if absolute:
            return str(self.path)
        elif base:
            if base.is_dir():
                return os.path.relpath(self.path, start = base)
            else:
                return os.path.relpath(self.path, start = base.parent)
        else: 
            return str(self.path.name)
           
class ExtInf(M3UEntry):
    def __init__(self, line: str, parent: Path = Path("")):
        super().__init__(line)

        self.text = self.raw[len("#EXTINF:"):]

    def __repr__(self):
        return f"<ExtInf: {self.text}>"
    
    def print(self):
        return f"#EXTINF: {self.text}"

class Track(M3UEntry):
    def __init__(self, line, parent: Path = Path("")):
        super().__init__(line)

        if isinstance(line, str):
            self.path = Path(self.raw)
        elif isinstance(line, Path):
            self.path = line

        if not self.path.is_absolute():
            self.path = (parent.parent / self.path).resolve()

        self.extinf = None  # Will be attached later

    def attach_extinf(self, extinf):
        self.extinf = extinf

    def __repr__(self):
        if self.extinf:
            return f"<Track: {repr(self.extinf)} -> {self.path}>"
        return f"<Track: {self.path}>"
    
    def print(self, absolute = False, base: Path = None):
        if absolute:
            return str(self.path)
        elif base:
            if base.is_dir():
                return os.path.relpath(self.path, start = base)
            else:
                return os.path.relpath(self.path, start = base.parent)
        else: 
            return str(self.path.name)
        
    def printExtInf(self):
        if isinstance(self.extinf, ExtInf):
            return self.extinf.print()
        else: return None