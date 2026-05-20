import os
import re
import sys
import asyncio
import asyncssh
import yaml

LOG_DIR = "logs"


def load_inventory(file_path: str) -> list:
    """Load node inventory from a YAML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('nodes', [])
    except FileNotFoundError:
        print(f"[Error] Inventory file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"[Error] YAML parsing error: {e}", file=sys.stderr)
        sys.exit(1)


def strip_rich(text: str) -> str:
    """Remove Rich markup tags like [green]...[/] from a string."""
    return re.sub(r'\[.*?\]', '', text)


async def run_command_on_node(node: dict, command: str, use_sudo: bool, timeout: int) -> dict:
    host = node['host']
    user = node['user']
    name = node['name']

    final_command = f"sudo {command}" if use_sudo else command
    os.makedirs(LOG_DIR, exist_ok=True)
    log_filepath = os.path.join(LOG_DIR, f"{name}_result.log")

    try:
        async def _run():
            async with asyncssh.connect(host, username=user) as conn:
                return await conn.run(final_command, check=False)

        if timeout and timeout > 0:
            result = await asyncio.wait_for(_run(), timeout=timeout)
        else:
            result = await _run()

        out_text = result.stdout.strip() if result.stdout else ""
        err_text = result.stderr.strip() if result.stderr else ""

        with open(log_filepath, 'w', encoding='utf-8') as f:
            f.write(f"=== Command: {final_command} ===\n")
            if out_text:
                f.write(f"[STDOUT]\n{out_text}\n")
            if err_text:
                f.write(f"\n[STDERR]\n{err_text}\n")

        raw_lines = out_text.split('\n') if result.exit_status == 0 else err_text.split('\n')
        lines = [l for l in raw_lines if l]
        if len(lines) > 15:
            display = '\n'.join(lines[:15]) + f"\n... ({len(lines)} lines total — see {log_filepath})"
        else:
            display = '\n'.join(lines)

        if result.exit_status == 0:
            return {"node": name, "host": host, "status": "[green]✅ Success[/]",
                    "log": log_filepath, "error": "", "display": display}
        else:
            return {"node": name, "host": host, "status": "[red]❌ Failed[/]",
                    "log": log_filepath, "error": f"Exit {result.exit_status}", "display": display}

    except asyncio.TimeoutError:
        return {"node": name, "host": host, "status": "[yellow]⏱️ Timeout[/]",
                "log": "-", "error": f"Timed out after {timeout}s", "display": ""}
    except Exception as e:
        return {"node": name, "host": host, "status": "[red]🚨 Error[/]",
                "log": "-", "error": str(e), "display": ""}


async def copy_file_to_node(node: dict, src: str, dest: str, use_sudo: bool, timeout: int) -> dict:
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
                    stderr=asyncio.subprocess.PIPE,
                )
                async with asyncssh.connect(host, username=user) as conn:
                    remote_cmd = f"sudo tar xzf - -C {dest}" if use_sudo else f"tar xzf - -C {dest}"
                    mkdir_cmd = f"sudo mkdir -p {dest}" if use_sudo else f"mkdir -p {dest}"
                    await conn.run(mkdir_cmd, check=True)
                    async with conn.create_process(remote_cmd, encoding=None) as process:
                        while True:
                            chunk = await proc.stdout.read(65536)
                            if not chunk:
                                break
                            process.stdin.write(chunk)
                            await process.stdin.drain()
                        process.stdin.write_eof()
                        await process.wait()
                        if process.exit_status != 0:
                            raise Exception(f"Remote tar failed (exit {process.exit_status})")
                    await proc.wait()
                    if proc.returncode != 0:
                        raise Exception(f"Local tar failed (exit {proc.returncode})")
                return "📁 Tar-Stream (root)" if use_sudo else "📁 Tar-Stream"
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

        return {"node": name, "host": host, "status": "[green]✅ Copied[/]",
                "display": f"{action} → {dest}"}

    except asyncio.TimeoutError:
        return {"node": name, "host": host, "status": "[yellow]⏱️ Timeout[/]",
                "display": f"Timed out after {timeout}s"}
    except Exception as e:
        return {"node": name, "host": host, "status": "[red]🚨 Error[/]",
                "display": str(e)}
