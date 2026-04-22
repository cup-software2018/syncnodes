import os
import sys
import yaml
import asyncio
import asyncssh
import argparse
from utils import load_inventory

# 2. Async function for FILE COPY (SFTP)


async def copy_file_to_node(node: dict, src: str, dest: str, use_sudo: bool):
    host = node['host']
    user = node['user']
    name = node['name']

    try:
        # Assumes SSH key-based authentication is already set up
        async with asyncssh.connect(host, username=user) as conn:
            if use_sudo:
                # 3-step process for root permissions:
                # SFTP to /tmp -> sudo mv -> sudo chown
                filename = os.path.basename(src)
                tmp_path = f"/tmp/{filename}"

                # Step 1: Upload to /tmp as the standard user
                async with conn.start_sftp_client() as sftp:
                    await sftp.put(src, tmp_path)

                # Step 2: Move the file to the final destination using sudo
                await conn.run(f"sudo mv {tmp_path} {dest}", check=True)

                # Step 3: Change ownership to root
                await conn.run(f"sudo chown root:root {dest}", check=True)

                print(f"📦 ✅ [{name} ({host})] Copied to {dest} (Owner: root)")
            else:
                # Direct SFTP upload if no sudo is required
                async with conn.start_sftp_client() as sftp:
                    await sftp.put(src, dest)

                print(
                    f"📦 ✅ [{name} ({host})] Copied to {dest} (Owner: {user})")

    except Exception as e:
        # Catch connection, authentication, or copy errors
        print(f"🚨 [{name} ({host})] Copy Error: {str(e)}\n", file=sys.stderr)

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

    args = parser.parse_args()

    # Check if local source file exists before starting connections
    if not os.path.exists(args.src):
        print(f"Error: Local file '{args.src}' does not exist.")
        sys.exit(1)

    # Load inventory
    nodes = load_inventory(args.inventory)
    if not nodes:
        print("No target nodes found in the inventory.")
        sys.exit(0)

    print(f"Copying '{args.src}' to {len(nodes)} nodes...\n" + "="*50)

    # Create and run concurrent tasks for all nodes
    tasks = [copy_file_to_node(
        node, args.src, args.dest, args.sudo) for node in nodes]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Gracefully run the asyncio event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExecution canceled by user.")
