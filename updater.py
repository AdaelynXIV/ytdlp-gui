import ctypes
import os
import subprocess
import sys
import time


def wait_for_process(process_id):
    if os.name != "nt":
        time.sleep(2)
        return

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(0x00100000, False, process_id)
    if handle:
        kernel32.WaitForSingleObject(handle, 30000)
        kernel32.CloseHandle(handle)
    else:
        time.sleep(2)


def install_update(application_path, update_path, process_id):
    wait_for_process(process_id)
    backup_path = f"{application_path}.old.{os.getpid()}"
    try:
        os.replace(application_path, backup_path)
        os.replace(update_path, application_path)
        try:
            os.remove(backup_path)
        except PermissionError:
            pass
        subprocess.Popen([application_path], cwd=os.path.dirname(application_path))
    except Exception:
        if os.path.exists(backup_path) and not os.path.exists(application_path):
            os.replace(backup_path, application_path)
        raise
    finally:
        if os.path.exists(update_path):
            os.remove(update_path)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: updater.exe APP_PATH UPDATE_PATH PROCESS_ID")
    install_update(sys.argv[1], sys.argv[2], int(sys.argv[3]))
