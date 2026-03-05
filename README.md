# M3U TOOLS

A command-line tool for **handling `.m3u` / `.m3u8` playlists**.

This utility helps with handling playlists that contain:

- nested playlists
- directories
- relative or absolute paths
- comments and metadata

---

## Installation

Go to the latest release
Download the `.whl` file

Install:

```bash
pip install file.whl
```
or 
```bash
pipx install file.whl
```

---

# Usage

Commands:

```
print
export
```

---

# Print Command

Displays the structure of a playlist as a **tree**.

```bash
m3u-tools print <file>
```

---

## Options

### Path formatting

```
--absolute
```

Display file paths as **absolute paths**.

```
--relative-root
```

Display paths relative to the **root playlist**.

```
--relative-parent
```

Display paths relative to the **parent playlist/directory**.

---

### Expansion options

```
--expand-playlist
--shrink-playlist
```

Expand or collapse nested playlists.

```
--expand-dir
--shrink-dir
```

Expand or collapse directories referenced in the playlist.

---

### Display options

```
--display-empty
```

Show empty lines.

```
--display-comment
```

Show comment lines.

```
--display-extinf
```

Show `#EXTINF` metadata.

---

# Export Command

Exports a processed playlist to a new `.m3u` or `.m3u8` file.

```bash
m3u-tools export <file> <export-path>
```

---

## Options

### Path handling

```
--absolute
--relative
```

Choose whether exported paths should be absolute or relative.

(Default: relative)

---

### Flattening

```
--flatten-playlist
```

Write out the contents of nested playlists instead of referencing them.

```
--flatten-dir
```

Write out files inside referenced directories.

---

### Cleanup options

```
--remove-empty
```

Remove empty lines.

```
--remove-comment
```

Remove comment lines.

```
--remove-extinf
```

Remove `#EXTINF` metadata.

---

# License

MIT License