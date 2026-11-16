import os
import re
import sys
import shutil
from scanner import format_size, CATEGORIES

CATEGORY_FOLDER_NAMES = {
    'video': '01_Videos_and_Movies',
    'archive': '02_Archives_and_Disk_Images',
    'installer': '03_Installers_and_Programs',
    'document': '04_Documents_and_PDFs',
    'audio': '05_Audio_and_Music',
    'image': '06_Images_and_Photos',
    'database': '07_Databases_and_Backups',
    'other': '08_Other_Large_Files'
}

def sanitize_filename(name):
    # Windows forbidden characters: \ / : * ? " < > |
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', name)
    return sanitized.strip()

def create_windows_shortcut(shortcut_path, target_path, description=""):
    try:
        import win32com.client
        shell = win32com.client.Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        if description:
            shortcut.Description = description[:1000]
        shortcut.Save()
        return True
    except Exception as e:
        # Fallback to PowerShell if win32com fails
        try:
            import subprocess
            ps_code = f"""
            $ws = New-Object -ComObject WScript.Shell
            $s = $ws.CreateShortcut('{shortcut_path.replace("'", "''")}')
            $s.TargetPath = '{target_path.replace("'", "''")}'
            $s.WorkingDirectory = '{os.path.dirname(target_path).replace("'", "''")}'
            $s.Save()
            """
            subprocess.run(['powershell', '-NoProfile', '-Command', ps_code], check=True, capture_output=True)
            return True
        except Exception as e2:
            return False

def generate_shortcuts(files, output_dir=r'c:\finder\Shortcuts', max_overall=100, max_per_cat=50):
    """
    files: list of dicts sorted descending by size:
           {'path': ..., 'name': ..., 'size': ..., 'category': ..., 'size_str': ...}
    """
    os.makedirs(output_dir, exist_ok=True)

    # Folders
    top_dir = os.path.join(output_dir, '00_Top_100_Largest_Overall')
    os.makedirs(top_dir, exist_ok=True)

    cat_dirs = {}
    for cat_id, folder_name in CATEGORY_FOLDER_NAMES.items():
        cat_path = os.path.join(output_dir, folder_name)
        os.makedirs(cat_path, exist_ok=True)
        cat_dirs[cat_id] = cat_path

    # Clean existing shortcuts in subdirectories
    for root, dirs, filenames in os.walk(output_dir):
        if root == output_dir:
            continue
        for fn in filenames:
            if fn.lower().endswith('.lnk'):
                try:
                    os.remove(os.path.join(root, fn))
                except OSError:
                    pass

    total_created = 0

    # 1. Generate Top Overall
    for idx, f in enumerate(files[:max_overall], start=1):
        clean_name = sanitize_filename(f['name'])
        size_str = f['size_str']
        lnk_name = f"Rank_{idx:03d} - [{size_str}] - {clean_name}.lnk"
        # Avoid Windows MAX_PATH (>255) issues
        if len(lnk_name) > 180:
            name_part, ext_part = os.path.splitext(clean_name)
            clean_name = name_part[:120] + ext_part
            lnk_name = f"Rank_{idx:03d} - [{size_str}] - {clean_name}.lnk"
            
        shortcut_path = os.path.join(top_dir, lnk_name)
        desc = f"Size: {size_str} | Original: {f['path']}"
        if create_windows_shortcut(shortcut_path, f['path'], desc):
            total_created += 1

    # 2. Generate per Category
    cat_counts = {c: 0 for c in CATEGORIES}
    for f in files:
        cat = f.get('category', 'other')
        if cat_counts.get(cat, 0) >= max_per_cat:
            continue

        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        rank = cat_counts[cat]
        target_folder = cat_dirs.get(cat, cat_dirs['other'])
        clean_name = sanitize_filename(f['name'])
        size_str = f['size_str']
        lnk_name = f"Rank_{rank:03d} - [{size_str}] - {clean_name}.lnk"
        if len(lnk_name) > 180:
            name_part, ext_part = os.path.splitext(clean_name)
            clean_name = name_part[:120] + ext_part
            lnk_name = f"Rank_{rank:03d} - [{size_str}] - {clean_name}.lnk"

        shortcut_path = os.path.join(target_folder, lnk_name)
        desc = f"Size: {size_str} | Category: {CATEGORIES[cat]['name']} | Original: {f['path']}"
        if create_windows_shortcut(shortcut_path, f['path'], desc):
            total_created += 1

    # 3. Create helper instructions and batch script in output_dir
    readme_path = os.path.join(output_dir, 'README_HOW_TO_USE.txt')
    with open(readme_path, 'w', encoding='utf-8') as rf:
        rf.write(
"""========================================================================
     C: DRIVE LARGE FILES - SHORTCUTS DIRECTORY
========================================================================

Every shortcut in these folders links to a large file found on your C: drive.
Shortcuts are ranked by size (largest first) and categorized into folders:

  - 00_Top_100_Largest_Overall/  -> The 100 biggest files on your C: drive
  - 01_Videos_and_Movies/        -> Movies, recordings, and videos
  - 02_Archives_and_Disk_Images/ -> ZIP, RAR, 7Z, ISO, VM disks
  - 03_Installers_and_Programs/  -> Setup files, EXEs, MSIs
  - 04_Documents_and_PDFs/       -> PDFs, Office docs, large sheets
  - 05_Audio_and_Music/          -> Music, audio files
  - 06_Images_and_Photos/        -> Photos, RAW images, designs
  - 07_Databases_and_Backups/    -> Database dumps, SQL backups
  - 08_Other_Large_Files/        -> Other unclassified large files

------------------------------------------------------------------------
HOW TO DELETE FILES YOU DON'T WANT:
------------------------------------------------------------------------

METHOD 1: Right-Click Shortcut -> Open File Location
  1. Browse any folder above to find files you want to remove.
  2. Right-click the shortcut.
  3. Click "Open file location" in the Windows menu.
  4. Windows Explorer will open right at the original file and select it!
  5. Press 'Delete' (or Shift+Delete) to remove it.

METHOD 2: Drag & Drop onto "Drag_Shortcuts_Here_To_Delete_Originals.bat"
  1. Select any shortcut(s) you don't want.
  2. Drag and drop them directly onto the batch file:
     "Drag_Shortcuts_Here_To_Delete_Originals.bat"
  3. It will confirm with you and safely send the REAL files to the
     Windows Recycle Bin (so you can restore them if needed)!

METHOD 3: Use the Interactive Web Dashboard
  1. In the browser dashboard that opened when you ran run.bat:
     Click [📂 Open in Explorer] or [🗑️ Move to Recycle Bin] directly!
========================================================================
"""
        )

    # 4. Create Drag_Shortcuts_Here_To_Delete_Originals.bat in output_dir
    drag_bat_path = os.path.join(output_dir, 'Drag_Shortcuts_Here_To_Delete_Originals.bat')
    with open(drag_bat_path, 'w', encoding='utf-8') as df:
        df.write(
r"""@echo off
setlocal
title Delete Original Files via Shortcut Dropper
cd /d "%~dp0"

if "%~1"=="" (
    echo.
    echo ====================================================================
    echo   DRAG AND DROP SHORTCUTS HERE TO DELETE ORIGINAL FILES
    echo ====================================================================
    echo.
    echo   How to use:
    echo   Select one or more shortcuts from the subfolders, and DRAG and DROP
    echo   them directly onto this file!
    echo.
    echo   The program will ask you for confirmation, then safely move the
    echo   real files to the Windows Recycle Bin.
    echo.
    echo ====================================================================
    pause
    exit /b
)

python "%~dp0..\delete_helper.py" %*
pause
"""
        )

    return total_created
