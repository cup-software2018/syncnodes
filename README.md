# syncnodes

`syncnodes` is a lightweight, asynchronous Python toolset designed for managing operations across a cluster of servers concurrently via SSH. Built on top of `asyncio` and `asyncssh`, it allows commands to be executed and files to be distributed to multiple nodes simultaneously, drastically reducing management time.

## Features

* **Asynchronous Execution:** Run shell commands and copy files to all nodes in parallel.
* **Remote Command Execution (`nodectl.py`):** Execute arbitrary SSH shell commands across your cluster.
* **File & Directory Distribution (`copyctl.py`):** Push local files and whole directory trees to remote destinations recursively over SFTP.
* **Execution Timeout:** Stop unresponsive workers from blocking sequences via the `--timeout` parameter.
* **Group Targeting:** Easily filter your execution scope down to subsets of your cluster using YAML `group` attributes.
* **Sudo Support:** Seamlessly execute commands and copy files to restricted directories using `--sudo` (requires passwordless sudo).
* **Rich Dashboard UI:** Enjoy a beautiful live progress spinner and post-execution summary tables built on `rich`.
* **Centralized Logging:** Detailed logs of standard output and standard error for `nodectl.py` executions are automatically neatly saved per node in a local `logs/` directory.
* **Simple Inventory Management:** Manage your target nodes easily through a YAML inventory file.

## Prerequisites

* Python 3.7+
* SSH key-based authentication must be set up properly between the current user and the target node users.
* Passwordless `sudo` must be configured for the target user on the remote nodes if you intend to use the `--sudo` flags.

#### Configuring Passwordless Sudo
To allow a user (e.g., `johndoe`) to execute `sudo` commands without a password prompt, you must edit the `/etc/sudoers` file on the target nodes. 
**Run `sudo visudo`** and add the following line at the end of the file:
```text
johndoe ALL=(ALL) NOPASSWD: ALL
```
*(Replace `johndoe` with your actual username)*

### Dependencies

Install the necessary Python requirements:

```bash
pip install asyncssh pyyaml rich
```

## Configuration

Define your node inventory in a YAML file (e.g., `nodes.yml`). The tool uses this file to connect to multiple hosts.

Example `nodes.yml`:
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
  # List all your cluster nodes here
```

## Usage

### 1. `nodectl.py` - Command Execution Manager

Run a CLI command across all nodes concurrently.

**Arguments:**
* `-i`, `--inventory`: Path to the inventory YAML file (default: `nodes.yml`)
* `-c`, `--command`: Linux command to execute (required)
* `-g`, `--group`: Target a specific group from `nodes.yml`
* `-t`, `--timeout`: Timeout in seconds (default: 0 / no timeout)
* `--sudo`: Execute command with `sudo` privileges

**Examples:**

```bash
# Check the disk usage on all targets in the 'control' group (nodes.yml is implicit)
python nodectl.py -c "df -h" -g control

# Clean up a system directory requiring sudo, limiting hanging to 5s
python nodectl.py -c "rm -rf /tmp/cache_folder" --sudo -t 5
```

### 2. `copyctl.py` - File & Directory Distribution Tool

Distribute a local file or recursive directory structure to nodes concurrently using SFTP. Handles proper user/root ownership automatically.

**Arguments:**
* `-i`, `--inventory`: Path to the inventory YAML file (default: `nodes.yml`)
* `-s`, `--src`: Local source file or directory path (required)
* `-d`, `--dest`: Remote destination file or directory path (required)
* `-g`, `--group`: Target a specific group from `nodes.yml`
* `-t`, `--timeout`: Timeout in seconds
* `--sudo`: Copy file/folder utilizing `sudo` (temporarily stages in `/tmp`, moves using `sudo`, and resets ownership to `root:root`)

**Examples:**

```bash
# Push an executable script to the 'worker' group
python copyctl.py -s ./start_service.sh -d /home/johndoe/start_service.sh -g worker

# Recursively distribute a root-owned configurations folder across the cluster
python copyctl.py -s ./ansible_configs -d /etc/ansible --sudo
```
