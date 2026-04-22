import os
import sys
import yaml
import asyncio
import asyncssh
import argparse
from utils import load_inventory
from rich.console import Console
from rich.table import Table

# 2. Async function for FILE COPY (SFTP)


async def copy_file_to_node(node: dict, src: str, dest: str, use_sudo: bool, timeout: int):
    host = node['host']
    user = node['user']
    name = node['name']
    
    isdir = os.path.isdir(src)

    try:
        async def _copy():
            async with asyncssh.connect(host, username=user) as conn:
                if use_sudo:
                    filename = os.path.basename(src.rstrip('/'))
                    tmp_path = f"/tmp/{filename}"

                    async with conn.start_sftp_client() as sftp:
                        await sftp.put(src, tmp_path, recurse=isdir)

                    if isdir:
                        await conn.run(f"sudo cp -r {tmp_path} {dest}", check=True)
                        await conn.run(f"sudo rm -rf {tmp_path}", check=True)
                        await conn.run(f"sudo chown -R root:root {dest}", check=True)
                        action_type = "📁 Directory (root)"
                    else:
                        await conn.run(f"sudo mv {tmp_path} {dest}", check=True)
                        await conn.run(f"sudo chown root:root {dest}", check=True)
                        action_type = "📄 File (root)"
                    return action_type
                else:
                    async with conn.start_sftp_client() as sftp:
                        await sftp.put(src, dest, recurse=isdir)
                    return "📁 Directory" if isdir else "📄 File"

        if timeout and timeout > 0:
            action = await asyncio.wait_for(_copy(), timeout=timeout)
        else:
            action = await _copy()

        return {"node": name, "host": host, "status": "[green]✅ Copied[/]", "details": f"{action} -> {dest}"}

    except asyncio.TimeoutError:
        return {"node": name, "host": host, "status": "[yellow]⏱️ Timeout[/]", "details": f"Timed out after {timeout}s"}
    except Exception as e:
        return {"node": name, "host": host, "status": "[red]🚨 Error[/]", "details": str(e)}

# 3. Main execution flow


async def main():
    # Setup argparse specifically for the copy tool
    parser = argparse.ArgumentParser(
        description="syncnodes File Copy Tool (copyctl)")

    parser.add_argument("-i", "--inventory", default="nodes.yml",
                        help="Path to the inventory YAML file")
    parser.add_argument("-s", "--src", required=True,
                        help="Local source file path")
    parser.add_argument("-d", "--dest", required=True,
                        help="Remote destination file path")
    parser.add_argument("--sudo", action="store_true",
                        help="Copy file with sudo (changes ownership to root)")
    parser.add_argument("-g", "--group", help="Target a specific group from nodes.yml")
    parser.add_argument("-t", "--timeout", type=int, default=0, help="Timeout in seconds")

    args = parser.parse_args()

    # Check if local source file exists before starting connections
    if not os.path.exists(args.src):
        print(f"Error: Local file '{args.src}' does not exist.")
        sys.exit(1)

    # Load inventory
    nodes = load_inventory(args.inventory)
    
    # Filter nodes by group if specified
    if args.group:
        nodes = [n for n in nodes if n.get('group') == args.group]

    if not nodes:
        print("No target nodes found in the inventory matching criteria.")
        sys.exit(0)

    console = Console()
    
    tasks = [copy_file_to_node(node, args.src, args.dest, args.sudo, args.timeout) for node in nodes]
    
    with console.status(f"[bold cyan]Pushing '{args.src}' to {len(nodes)} nodes...[/]", spinner="dots"):
        results = await asyncio.gather(*tasks)

    # Render summary table
    table = Table(title="Copy Summary", show_header=True, header_style="bold magenta")
    table.add_column("Node", style="cyan")
    table.add_column("Host", style="blue")
    table.add_column("Status")
    table.add_column("Details", style="dim")

    for res in results:
        table.add_row(res['node'], res['host'], res['status'], res['details'])

    console.print(table)

if __name__ == "__main__":
    # Gracefully run the asyncio event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExecution canceled by user.")
