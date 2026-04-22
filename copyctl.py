import os
import sys
import yaml
import asyncio
import asyncssh
import argparse
from utils import load_inventory

# 2. Async function for FILE COPY (SFTP)


async def copy_file_to_node(node: dict, src: str, dest: str, use_sudo: bool, timeout: int):
    host = node['host']
    user = node['user']
    name = node['name']
    
    isdir = os.path.isdir(src)

    try:
        async def _copy():
            if isdir:
                src_parent = os.path.dirname(src.rstrip('/'))
                src_base = os.path.basename(src.rstrip('/'))
                proc = await asyncio.create_subprocess_exec(
                    "tar", "czf", "-", "-C", src_parent, src_base,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                async with asyncssh.connect(host, username=user) as conn:
                    if use_sudo:
                        await conn.run(f"sudo mkdir -p {dest}", check=True)
                        async with conn.create_process(f"sudo tar xzf - -C {dest}", encoding=None) as process:
                            while True:
                                chunk = await proc.stdout.read(65536)
                                if not chunk: break
                                process.stdin.write(chunk)
                                await process.stdin.drain()
                            process.stdin.write_eof()
                            await process.wait()
                            if process.exit_status != 0: 
                                raise Exception(f"Tar stream failed remotely (Exit: {process.exit_status})")
                        await proc.wait()
                        if proc.returncode != 0: 
                            raise Exception(f"Tar stream failed locally (Exit: {proc.returncode})")
                        return "📁 Tar-Stream (root)"
                    else:
                        await conn.run(f"mkdir -p {dest}", check=True)
                        async with conn.create_process(f"tar xzf - -C {dest}", encoding=None) as process:
                            while True:
                                chunk = await proc.stdout.read(65536)
                                if not chunk: break
                                process.stdin.write(chunk)
                                await process.stdin.drain()
                            process.stdin.write_eof()
                            await process.wait()
                            if process.exit_status != 0: 
                                raise Exception(f"Tar stream failed remotely (Exit: {process.exit_status})")
                        await proc.wait()
                        if proc.returncode != 0: 
                            raise Exception(f"Tar stream failed locally (Exit: {proc.returncode})")
                        return "📁 Tar-Stream"
            else:
                async with asyncssh.connect(host, username=user) as conn:
                    if use_sudo:
                        filename = os.path.basename(src)
                        tmp_path = f"/tmp/{filename}"
                        async with conn.start_sftp_client() as sftp:
                            await sftp.put(src, tmp_path)
                        await conn.run(f"sudo mv {tmp_path} {dest}", check=True)
                        await conn.run(f"sudo chown root:root {dest}", check=True)
                        return "📄 File (root)"
                    else:
                        async with conn.start_sftp_client() as sftp:
                            await sftp.put(src, dest)
                        return "📄 File"

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
    parser.add_argument("--no-rich", action="store_true", help="Disable Rich UI output")

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

    tasks = [copy_file_to_node(node, args.src, args.dest, args.sudo, args.timeout) for node in nodes]
    
    rich_success = False
    if not args.no_rich:
        try:
            from rich.console import Console
            from rich.table import Table
            console = Console()
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
            rich_success = True
        except ImportError:
            print("Warning: The 'rich' module is not installed. Falling back to simple output.\n")

    if not rich_success:
        print(f"Copying '{args.src}' to {len(nodes)} nodes...\n" + "="*50)
        results = await asyncio.gather(*tasks)
        import re
        for res in results:
            clean_status = re.sub(r'\[.*?\]', '', res['status'])
            print(f"[{res['node']} ({res['host']})] {clean_status} -> {res['details']}")

if __name__ == "__main__":
    # Gracefully run the asyncio event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExecution canceled by user.")
