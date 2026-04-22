import os
import sys
import yaml
import asyncio
import asyncssh
import argparse
from utils import load_inventory

# Create a directory to store long outputs
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 2. Async function to execute a command on a single node


async def run_command_on_node(node: dict, command: str, use_sudo: bool):
    host = node['host']
    user = node['user']
    name = node['name']

    # Prepend 'sudo ' if the option is enabled (assumes passwordless sudo is configured)
    final_command = f"sudo {command}" if use_sudo else command

    try:
        # Assumes SSH key-based authentication is already set up
        async with asyncssh.connect(host, username=user) as conn:
            result = await conn.run(final_command, check=False)

            # Safely handle None values if output is empty
            out_text = result.stdout.strip() if result.stdout else ""
            err_text = result.stderr.strip() if result.stderr else ""

            # 1) Save the full, untruncated output to a log file
            log_filepath = os.path.join(LOG_DIR, f"{name}_result.log")
            with open(log_filepath, 'w', encoding='utf-8') as log_file:
                log_file.write(f"=== Command: {final_command} ===\n")
                if out_text:
                    log_file.write(f"[STDOUT]\n{out_text}\n")
                if err_text:
                    log_file.write(f"\n[STDERR]\n{err_text}\n")

            # 2) Truncate the output for the terminal display (e.g., max 7 lines)
            max_lines = 7
            out_lines = out_text.split('\n') if out_text else []

            if len(out_lines) > max_lines:
                # Keep only the first few lines and add a truncation message
                display_text = '\n'.join(out_lines[:max_lines])
                display_text += f"\n\n... (Output truncated. Total {len(out_lines)} lines. See '{log_filepath}' for full details.)"
            else:
                display_text = out_text

            # 3) Print the summarized result to the terminal
            if result.exit_status == 0:
                print(
                    f"✅ [{name} ({host})] - Log saved to {log_filepath}\n{display_text}\n")
            else:
                # Command execution failed
                print(
                    f"❌ [{name} ({host})] Failed (Exit code {result.exit_status}):\n{err_text}\n", file=sys.stderr)

    except Exception as e:
        # Catch connection, authentication, or other SSH-related errors
        print(
            f"🚨 [{name} ({host})] Connection/Execution Error: {str(e)}\n", file=sys.stderr)

# 3. Main asynchronous execution flow


async def main():
    # Setup argparse for CLI options
    parser = argparse.ArgumentParser(
        description="Multi-node Linux CLI Manager")
    parser.add_argument("-i", "--inventory", default="inventory.yaml",
                        help="Path to the inventory YAML file")
    parser.add_argument("-c", "--command", required=True,
                        help="Linux command to execute")
    parser.add_argument("--sudo", action="store_true",
                        help="Execute command with sudo privileges")

    args = parser.parse_args()

    # Load nodes from the specified inventory file
    nodes = load_inventory(args.inventory)
    if not nodes:
        print("No target nodes found in the inventory.")
        sys.exit(0)

    print(f"Executing '{args.command}' on {len(nodes)} nodes...\n" + "="*50)

    # Create and run concurrent tasks for all nodes
    tasks = [run_command_on_node(node, args.command, args.sudo)
             for node in nodes]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Gracefully run the asyncio event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExecution canceled by user.")
