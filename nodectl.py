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

        # Create truncated display text (max 15 lines)
        max_lines = 15
        target_lines = out_text.split('\n') if result.exit_status == 0 else err_text.split('\n')
        target_lines = [line for line in target_lines if line] # Filter empty
        
        if len(target_lines) > max_lines:
            display_text = '\n'.join(target_lines[:max_lines]) + f"\n... (Output truncated. Total {len(target_lines)} lines. See log.)"
        else:
            display_text = '\n'.join(target_lines)

        # Return status dictionary instead of printing directly
        if result.exit_status == 0:
            return {"node": name, "host": host, "status": "[green]✅ Success[/]", "log": log_filepath, "error": "", "display": display_text}
        else:
            return {"node": name, "host": host, "status": "[red]❌ Failed[/]", "log": log_filepath, "error": f"Exit {result.exit_status}", "display": display_text}

    except asyncio.TimeoutError:
        return {"node": name, "host": host, "status": "[yellow]⏱️ Timeout[/]", "log": "-", "error": f"Timed out after {timeout}s", "display": ""}
    except Exception as e:
        return {"node": name, "host": host, "status": "[red]🚨 Error[/]", "log": "-", "error": str(e), "display": ""}

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
    parser.add_argument("--rich", action="store_true", help="Enable Rich UI output")

    args = parser.parse_args()

    # Load nodes from the specified inventory file
    nodes = load_inventory(args.inventory)
    
    # Filter nodes by group if specified
    if args.group:
        nodes = [n for n in nodes if n.get('group') == args.group]

    if not nodes:
        print("No target nodes found in the inventory matching criteria.")
        sys.exit(0)
    
    tasks = [run_command_on_node(node, args.command, args.sudo, args.timeout) for node in nodes]
    
    rich_success = False
    if args.rich:
        try:
            from rich.console import Console
            from rich.table import Table
            console = Console()
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
            rich_success = True
        except ImportError:
            print("Warning: The 'rich' module is not installed. Falling back to simple output.\n")

    if not rich_success:
        print(f"Executing '{args.command}' on {len(nodes)} nodes...\n" + "="*50)
        results = await asyncio.gather(*tasks)
        import re
        for res in results:
            clean_status = re.sub(r'\[.*?\]', '', res['status'])
            details = res['log'] if "Success" in res['status'] else f"{res['log']} | {res['error']}"
            print(f"[{res['node']} ({res['host']})] {clean_status} -> {details}")
            if res.get('display'):
                print(f"{res['display']}\n")

if __name__ == "__main__":
    # Gracefully run the asyncio event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExecution canceled by user.")
