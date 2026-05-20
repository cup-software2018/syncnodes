# syncnodes

A lightweight async Python toolset for managing multiple servers over SSH — run commands and distribute files across your cluster in parallel.

Includes a **GUI** (`syncnodes`) and two **CLI tools** (`nodectl`, `copyctl`), all backed by a shared async core (`utils.py`).

## Features

- **Parallel execution** — async SSH via `asyncio` + `asyncssh`; all nodes run concurrently
- **GUI** — wizard-style PySide6 app: select nodes → configure action → view results
- **`nodectl`** — run shell commands across the cluster
- **`copyctl`** — push files or entire directory trees over SFTP
- **Group targeting** — filter nodes by `group` field in inventory
- **Sudo support** — passwordless sudo for restricted destinations
- **Timeout** — per-operation timeout to avoid hanging
- **Rich output** — live spinner + summary table in the terminal (optional)
- **Per-node logs** — full stdout/stderr saved to `logs/<node>_result.log`

## Installation

```bash
./install.sh
```

Installs dependencies, copies files to `~/.local/lib/syncnodes/`, registers the app in the GNOME app grid, and creates symlinks in `~/.local/bin/`.

Or install dependencies manually:

```bash
pip install -r requirements.txt
```

## Prerequisites

- Python 3.7+
- SSH key-based authentication to all target nodes
- Passwordless `sudo` on remote nodes if using `--sudo`

To enable passwordless sudo for a user (e.g. `johndoe`), run `sudo visudo` on each target node and add:

```text
johndoe ALL=(ALL) NOPASSWD: ALL
```

## Inventory

Create a `nodes.yml` in the project directory (see `nodes.yml.example`):

```yaml
nodes:
  - name: node1
    host: 192.168.1.11
    user: johndoe
    group: control
  - name: node2
    host: 192.168.1.12
    user: johndoe
    group: worker
```

## GUI

```bash
./syncnodes
# or after install:
syncnodes
```

Three-step wizard:
1. **Select Nodes** — pick from inventory, filter by group
2. **Set Action** — Command or Copy, with timeout and sudo options
3. **Results** — per-node status and output log

## CLI

### `nodectl` — Command Execution

```bash
# Run on all nodes
./nodectl -c "uptime"

# Target a group with sudo and timeout
./nodectl -c "systemctl restart nginx" -g worker --sudo -t 30

# Rich table output
./nodectl -c "df -h" --rich
```

| Flag | Description |
|------|-------------|
| `-i` | Inventory file (default: `nodes.yml`) |
| `-c` | Command to run (required) |
| `-g` | Target group |
| `-t` | Timeout in seconds |
| `--sudo` | Run with sudo |
| `--rich` | Enable Rich UI |

### `copyctl` — File & Directory Distribution

```bash
# Push a file to all nodes
./copyctl -s ./deploy.sh -d /home/johndoe/deploy.sh

# Recursively push a directory as root to a group
./copyctl -s ./configs -d /etc/myapp -g control --sudo
```

| Flag | Description |
|------|-------------|
| `-i` | Inventory file (default: `nodes.yml`) |
| `-s` | Local source file or directory (required) |
| `-d` | Remote destination path (required) |
| `-g` | Target group |
| `-t` | Timeout in seconds |
| `--sudo` | Stage in `/tmp`, move with sudo, set `root:root` ownership |
| `--no-rich` | Disable Rich UI |

## Project Structure

```
syncnodes        # GUI application (PySide6)
nodectl          # CLI: remote command execution
copyctl          # CLI: file/directory distribution
utils.py         # Shared core: SSH functions, inventory loader
nodes.yml        # Your node inventory
requirements.txt # Python dependencies
install.sh       # GNOME desktop installer
syncnodes.svg    # App icon
```
