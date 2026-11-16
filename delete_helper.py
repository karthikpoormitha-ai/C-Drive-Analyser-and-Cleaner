import os
import sys
import ctypes
from ctypes import wintypes
from scanner import format_size

class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ('hwnd', wintypes.HWND),
        ('wFunc', wintypes.UINT),
        ('pFrom', wintypes.LPCWSTR),
        ('pTo', wintypes.LPCWSTR),
        ('fFlags', wintypes.UINT),
        ('fAnyOperationsAborted', wintypes.BOOL),
        ('hNameMappings', wintypes.LPVOID),
        ('lpszProgressTitle', wintypes.LPCWSTR)
    ]

FO_DELETE = 3
FOF_ALLOWUNDO = 0x0040
FOF_NOCONFIRMATION = 0x0010
FOF_SILENT = 0x0004

def send_to_recycle_bin(file_path):
    """
    Safely moves a file or folder to the Windows Recycle Bin.
    Returns True if successfully moved, False otherwise.
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        return False, "File does not exist"

    # SHFileOperationW requires a double-null-terminated string
    p_from = abs_path + '\x00\x00'
    fileop = SHFILEOPSTRUCTW()
    fileop.wFunc = FO_DELETE
    fileop.pFrom = p_from
    fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT

    try:
        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
        if res == 0 and not fileop.fAnyOperationsAborted:
            return True, "Successfully moved to Recycle Bin"
        else:
            return False, f"Failed with Windows error code {res}"
    except Exception as e:
        return False, str(e)

def resolve_shortcut(lnk_path):
    """Returns the target path of a .lnk file."""
    try:
        import win32com.client
        shell = win32com.client.Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(os.path.abspath(lnk_path))
        target = shortcut.TargetPath
        if target:
            return target
    except Exception:
        pass

    try:
        import subprocess
        ps_cmd = f"$sh = New-Object -ComObject WScript.Shell; $target = $sh.CreateShortcut('{os.path.abspath(lnk_path)}').TargetPath; Write-Output $target"
        res = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], capture_output=True, text=True)
        t = res.stdout.strip()
        if t:
            return t
    except Exception:
        pass
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python delete_helper.py <shortcut_or_file1.lnk> [file2.lnk ...]")
        return

    items = sys.argv[1:]
    print("=" * 65)
    print("      DRAG-AND-DROP FILE RECYCLER")
    print("=" * 65)
    print(f"Items dropped: {len(items)}\n")

    targets_to_delete = []
    for item in items:
        if item.lower().endswith('.lnk'):
            target = resolve_shortcut(item)
            if target and os.path.exists(target):
                size = os.path.getsize(target)
                targets_to_delete.append((item, target, size))
            elif target:
                print(f"[!] Target not found: {target}")
            else:
                print(f"[!] Could not resolve shortcut: {item}")
        else:
            if os.path.exists(item):
                size = os.path.getsize(item)
                targets_to_delete.append((None, item, size))

    if not targets_to_delete:
        print("No valid target files found to delete.")
        return

    print("Found files to delete:")
    total_freed_bytes = 0
    for idx, (lnk, target, size) in enumerate(targets_to_delete, start=1):
        print(f" {idx}. [{format_size(size)}] {target}")
        total_freed_bytes += size

    print("-" * 65)
    print(f"Total potential space to free: {format_size(total_freed_bytes)}")
    print("-" * 65)
    print("Files will be safely moved to your Windows Recycle Bin.")
    print("You can easily restore them from the Recycle Bin if needed.\n")

    confirm_all = False
    recycled_count = 0
    freed_actual = 0

    for idx, (lnk, target, size) in enumerate(targets_to_delete, start=1):
        if not confirm_all:
            ans = input(f"Recycle [{format_size(size)}] '{os.path.basename(target)}'? (Y=Yes / A=Yes to all / N=Skip / C=Cancel): ").strip().lower()
            if ans == 'c':
                print("Cancelled remaining items.")
                break
            elif ans == 'a':
                confirm_all = True
            elif ans != 'y':
                print(f"Skipped: {target}")
                continue

        success, msg = send_to_recycle_bin(target)
        if success:
            print(f" [OK] Recycled: {target}")
            recycled_count += 1
            freed_actual += size
            # Remove the shortcut file if it was provided
            if lnk and os.path.exists(lnk):
                try:
                    os.remove(lnk)
                except OSError:
                    pass
        else:
            print(f" [FAILED] Could not recycle {target}: {msg}")

    print("\n" + "=" * 65)
    print(f"Done! {recycled_count} file(s) moved to Recycle Bin.")
    print(f"Total disk space freed: {format_size(freed_actual)}")
    print("=" * 65)

if __name__ == '__main__':
    main()
