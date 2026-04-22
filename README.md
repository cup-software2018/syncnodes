# syncnodes

`syncnodes` is a lightweight, asynchronous Python toolset designed for managing operations across a cluster of servers concurrently via SSH. Built on top of `asyncio` and `asyncssh`, it allows commands to be executed and files to be distributed to multiple nodes simultaneously, drastically reducing management time.

## Features

* **Asynchronous Execution:** Run shell commands and copy files to all nodes in parallel.
* **Remote Command Execution (`nodectl.py`):** Execute arbitrary SSH shell commands across your cluster.
* **File Distribution (`copyctl.py`):** Push local files to remote destinations over SFTP.
* **Sudo Support:** Seamlessly execute commands and copy files to restricted directories using `--sudo` (requires passwordless sudo).
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
pip install asyncssh pyyaml
```

## Configuration

Define your node inventory in a YAML file (e.g., `nodes.yml`). The tool uses this file to connect to multiple hosts.

Example `nodes.yml`:
```yaml
nodes:
  - name: node1
    host: 192.168.1.11
    user: johndoe
  - name: node2
    host: 192.168.1.12
    user: johndoe
  # List all your cluster nodes here
```

## Usage

### 1. `nodectl.py` - Command Execution Manager

Run a CLI command across all nodes concurrently.

**Arguments:**
* `-i`, `--inventory`: Path to the inventory YAML file (default: `inventory.yaml`)
* `-c`, `--command`: Linux command to execute (required)
* `--sudo`: Execute command with `sudo` privileges

**Examples:**

```bash
# Check the disk usage on all nodes using nodes.yml
python nodectl.py -i nodes.yml -c "df -h"

# Clean up a system directory requiring sudo
python nodectl.py -i nodes.yml -c "rm -rf /tmp/cache_folder" --sudo
```

### 2. `copyctl.py` - File Distribution Tool

Distribute a local file to all nodes concurrently using SFTP. Handles proper user/root ownership automatically.

**Arguments:**
* `-i`, `--inventory`: Path to the inventory YAML file (default: `inventory.yaml`)
* `-s`, `--src`: Local source file path (required)
* `-d`, `--dest`: Remote destination file path (required)
* `--sudo`: Copy file utilizing `sudo` (temporarily stages in `/tmp`, moves using `sudo`, and resets ownership to `root:root`)

**Examples:**

```bash
# Push an executable script to user's home directories
python copyctl.py -i nodes.yml -s ./start_service.sh -d /home/amore2/start_service.sh

# Distribute a root-owned system config file across the cluster
python copyctl.py -i nodes.yml -s ./hosts.config -d /etc/hosts --sudo
```
