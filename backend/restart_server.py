"""
BeatCanvas Server Restart Script

Kills any existing processes on port 8002 and starts fresh.
Usage: python restart_server.py
"""

import subprocess
import sys
import time
import os

PORT = 8002

def get_pids_on_port(port):
    """Get all PIDs listening on the specified port."""
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True
        )
        pids = set()
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit():
                        pids.add(pid)
        return list(pids)
    except Exception as e:
        print(f"Error getting PIDs: {e}")
        return []

def kill_pids(pids):
    """Kill processes by PID."""
    for pid in pids:
        try:
            subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
            print(f"Killed process {pid}")
        except Exception as e:
            print(f"Could not kill {pid}: {e}")

def main():
    print(f"=== BeatCanvas Server Restart ===")

    # Find and kill existing processes on port
    pids = get_pids_on_port(PORT)
    if pids:
        print(f"Found processes on port {PORT}: {pids}")
        kill_pids(pids)
        time.sleep(1)  # Give OS time to release port
    else:
        print(f"No existing processes on port {PORT}")

    # Verify port is free
    pids = get_pids_on_port(PORT)
    if pids:
        print(f"WARNING: Port {PORT} still in use by {pids}")
        print("Waiting 2 more seconds...")
        time.sleep(2)

    # Start the server
    print(f"\nStarting server on port {PORT}...")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Replace current process with uvicorn
    os.execvp(sys.executable, [sys.executable, 'main.py'])

if __name__ == '__main__':
    main()
