# 🔍 C: Drive Disk Space Analyzer & File Cleaner

A high-speed disk scanner and space recovery tool for Windows. When you run `run.bat`, it scans your entire `C:\` drive at 50,000+ files per second, ranks every large file by size and category, and gives you direct shortcuts and 1-click tools so you can inspect and delete what you don't want.

---

## 🚀 How to Run

Simply **double-click** `run.bat`:
```cmd
run.bat
```

1. **Launches the High-Speed Scanner**: Begins scanning your entire `C:\` drive immediately in the background.
2. **Opens the Interactive Web Dashboard**: Automatically pops up in your default web browser (Edge/Chrome).
3. **Generates Windows Shortcuts**: Organizes the largest files into `c:\finder\Shortcuts` categorized by file type and ranked by size.

---

## 🌟 Features

### 1. Interactive Web Dashboard
* **Live Scanning Counter**: Shows real-time files analyzed, elapsed time, and current folder being inspected.
* **Category Breakdown**:
  * 🎬 **Videos & Movies** (`.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, etc.)
  * 📦 **Archives & Disk Images** (`.zip`, `.rar`, `.7z`, `.iso`, `.vmdk`, etc.)
  * 💿 **Installers & Programs** (`.exe`, `.msi`, `.apk`, etc.)
  * 📄 **Documents & PDFs** (`.pdf`, `.docx`, `.xlsx`, `.pptx`, etc.)
  * 🎵 **Audio & Music** (`.mp3`, `.wav`, `.flac`, etc.)
  * 🖼️ **Images & Photos** (`.png`, `.jpg`, `.raw`, `.psd`, etc.)
  * 💾 **Databases & Backups** (`.db`, `.sqlite`, `.bak`, `.sql`, etc.)
  * 📁 **Other Large Files**
* **Filters & Search**:
  * Filter by minimum size: All (> 1 MB), > 10 MB, > 50 MB, > 100 MB, > 500 MB, > 1 GB.
  * Real-time search by filename or folder path.
  * Sort by size (largest first), name, or date modified.
* **Direct Actions**:
  * 📂 **Reveal in Explorer**: Opens Windows Explorer with that exact file selected so you can review or delete it.
  * 🗑️ **Move to Recycle Bin**: Safely moves the file to the Windows Recycle Bin (with confirmation dialog) so you never lose data permanently by mistake.

---

### 2. Windows Shortcuts Folder (`c:\finder\Shortcuts`)
Every large file gets a shortcut formatted like:
`Rank_001 - [14.80 GB] - Video_File.mp4.lnk`

Organized into folders:
* `00_Top_100_Largest_Overall`
* `01_Videos_and_Movies`
* `02_Archives_and_Disk_Images`
* `03_Installers_and_Programs`
* `04_Documents_and_PDFs`
* `05_Audio_and_Music`
* `06_Images_and_Photos`
* `07_Databases_and_Backups`
* `08_Other_Large_Files`

#### How to Delete Files from the Shortcuts Folder:
* **Option A**: Right-click any shortcut ➔ Click **"Open file location"** ➔ Press `Delete` on your keyboard.
* **Option B**: Select any shortcut(s) and **drag & drop** them onto `Drag_Shortcuts_Here_To_Delete_Originals.bat` inside the Shortcuts folder. It will ask for confirmation and safely move the original files to the Windows Recycle Bin.
* **Option C**: Use the Web Dashboard directly!

---

## 🛠️ Technical Details
* **Zero External Dependencies**: Uses Python standard library + Windows Shell API (`SHFileOperationW` and `WScript.Shell`).
* **Safe Recycling**: Deletions go to the Windows Recycle Bin (`FOF_ALLOWUNDO`), allowing full recovery if needed.
* **Loop Protection**: Skips junction points, symlinks, and reparse points to prevent infinite loops.
* **System File Protection**: Ignores locked system roots like `$Recycle.Bin` and `System Volume Information`.
