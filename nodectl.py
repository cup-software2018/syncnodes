import os
import sys
import yaml
import asyncio
import asyncssh
import argparse
from utils import load_inventory
from rich.console import Console
from rich.table import Table

# Create a directory to store long outputs
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 2. Async function to execute a command on a single node


async def run_command_on_node(node: dict, command: str, use_sudo: bool, timeout: int):
    host = node['host']
    user = node['user']
    name = node['name']

    # Prepend 'sudo ' if the option is enabled (assumes passwordless sudo is configured)
    final_command = f"sudo {command}" if use_sudo else command
    log_filepath = os.path.join(LOG_DIR, f"{name}_result.log")

    try:
        async def _run():
            async with asyncssh.connect(host, username=user) as conn:
                return await conn.run(final_command, check=False)

        if timeout and timeout > 0:
            result = await asyncio.wait_for(_run(), timeout=timeout)
        else:
            result = await _run()

        # Safely handle None values if output is empty
        out_text = result.stdout.strip() if result.stdout else ""
        err_text = result.stderr.strip() if result.stderr else ""

        # Save the full, untruncated output to a log file
        with open(log_filepath, 'w', encoding='utf-8') as log_file:
            log_file.write(f"=== Command: {final_command} ===\n")
            if out_text:
                log_file.write(f"[STDOUT]\n{out_text}\n")
            if err_text:
                log_file.write(f"\n[STDERR]\n{err_text}\n")

        # Return status dictionary instead of printing directly
        if result.exit_status == 0:
            return {"node": name, "host": host, "status": "[green]✅ Success[/]", "log": log_filepath, "error": ""}
        else:
            return {"node": name, "host": host, "status": "[red]❌ Failed[/]", "log": log_filepath, "error": f"Exit {result.exit_status}"}

    except asyncio.TimeoutError:
        return {"node": name, "host": host, "status": "[yellow]⏱️ Timeout[/]", "log": "-", "error": f"Timed out after {timeout}s"}
    except Exception as e:
        return {"node": name, "host": host, "status": "[red]🚨 Error[/]", "log": "-", "error": str(e)}

# 3. Main asynchronous execution flow


async def main():
    # Setup argparse for CLI options
    parser = argparse.ArgumentParser(
        description="Multi-node Linux CLI Manager")
    parser.add_argument("-i", "--inventory", default="nodes.yml",
                        help="Path to the inventory YAML file")
    parser.add_argument("-c", "--command", required=True,
                        help="Linux command to execute")
    parser.add_argument("--sudo", action="store_true",
                        help="Execute command with sudo privileges")
    parser.add_argument("-g", "--group", help="Target a specific group from nodes.yml")
    parser.add_argument("-t", "--timeout", type=int, default=0, help="Timeout in seconds")

    args = parser.parse_args()

    # Load nodes from the specified inventory file
    nodes = load_inventory(args.inventory)
    
    # Filter nodes by group if specified
    if args.group:
        nodes = [n for n in nodes if n.get('group') == args.group]

    if not nodes:
        print("No target nodes found in the inventory matching criteria.")
        sys.exit(0)

    console = Console()
    
    tasks = [run_command_on_node(node, args.command, args.sudo, args.timeout) for node in nodes]
    
    with console.status(f"[bold cyan]Executing '{args.command}' on {len(nodes)} nodes...[/]", spinner="dots"):
        results = await asyncio.gather(*tasks)

    # Render summary table
    table = Table(title="Execution Summary", show_header=True, header_style="bold magenta")
    table.add_column("Node", style="cyan")
    table.add_column("Host", style="blue")
    table.add_column("Status")
    table.add_column("Details / Log", style="dim")

    for res in results:
        details = res['log'] if "Success" in res['status'] else f"{res['log']} | {res['error']}"
        table.add_row(res['node'], res['host'], res['status'], details)

    console.print(table)

if __name__ == "__main__":
    # Gracefully run the asyncio event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExecution canceled by user.")
