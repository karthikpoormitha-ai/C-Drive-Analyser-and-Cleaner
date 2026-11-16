import os
import sys
import time
import threading
from collections import deque

CATEGORIES = {
    'video': {
        'id': 'video',
        'name': 'Videos & Movies',
        'icon': '🎬',
        'exts': {
            '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', 
            '.m4v', '.mpg', '.mpeg', '.3gp', '.ts', '.vob', '.rmvb', '.mts', '.m2ts'
        }
    },
    'archive': {
        'id': 'archive',
        'name': 'Archives & Disk Images',
        'icon': '📦',
        'exts': {
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', 
            '.iso', '.img', '.vhd', '.vhdx', '.vmdk', '.qcow2', '.cab', '.wim', '.dmg'
        }
    },
    'installer': {
        'id': 'installer',
        'name': 'Installers & Programs',
        'icon': '💿',
        'exts': {
            '.exe', '.msi', '.msp', '.pkg', '.deb', '.rpm', '.apk', '.appx', '.msix'
        }
    },
    'audio': {
        'id': 'audio',
        'name': 'Audio & Music',
        'icon': '🎵',
        'exts': {
            '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', 
            '.opus', '.aiff', '.mid', '.midi', '.ape', '.alac'
        }
    },
    'image': {
        'id': 'image',
        'name': 'Images & Photos',
        'icon': '🖼️',
        'exts': {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', 
            '.raw', '.cr2', '.nef', '.psd', '.ai', '.svg', '.ico', '.heic'
        }
    },
    'document': {
        'id': 'document',
        'name': 'Documents & PDFs',
        'icon': '📄',
        'exts': {
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
            '.csv', '.txt', '.rtf', '.epub', '.odt', '.ods', '.odp'
        }
    },
    'database': {
        'id': 'database',
        'name': 'Databases & Backups',
        'icon': '💾',
        'exts': {
            '.db', '.sqlite', '.sqlite3', '.mdf', '.ldf', '.bak', '.sql', '.rdb', '.dump', '.dmp'
        }
    },
    'other': {
        'id': 'other',
        'name': 'Other Files',
        'icon': '📁',
        'exts': set()
    }
}

EXT_TO_CATEGORY = {}
for cat_id, cat_info in CATEGORIES.items():
    for ext in cat_info['exts']:
        EXT_TO_CATEGORY[ext] = cat_id

def get_category_for_file(filename):
    _, ext = os.path.splitext(filename.lower())
    return EXT_TO_CATEGORY.get(ext, 'other'), ext

def format_size(bytes_size):
    if bytes_size >= 1024 ** 4:
        return f"{bytes_size / (1024 ** 4):.2f} TB"
    elif bytes_size >= 1024 ** 3:
        return f"{bytes_size / (1024 ** 3):.2f} GB"
    elif bytes_size >= 1024 ** 2:
        return f"{bytes_size / (1024 ** 2):.2f} MB"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.2f} KB"
    else:
        return f"{bytes_size} B"

class DriveScanner:
    def __init__(self, root_drive='C:\\', min_size_bytes=1024*1024):
        self.root_drive = root_drive
        self.min_size_bytes = min_size_bytes
        self.lock = threading.Lock()
        
        # State
        self.is_scanning = False
        self.is_finished = False
        self.is_stopped = False
        self.start_time = 0
        self.elapsed_time = 0
        
        # Counters
        self.total_dirs_scanned = 0
        self.total_files_scanned = 0
        self.total_bytes_scanned = 0
        self.current_folder = ""
        
        # Files ranked
        # list of dicts: {'path': ..., 'name': ..., 'size': ..., 'size_str': ..., 'category': ..., 'ext': ..., 'mtime': ...}
        self.files = []
        
        # Category totals: {category_id: {'count': ..., 'bytes': ...}}
        self.category_stats = {cat: {'count': 0, 'bytes': 0} for cat in CATEGORIES}

        # Directories to skip
        self.skip_dirs = {
            '$recycle.bin', 'system volume information', 'recovery',
            'windows\\winsxs', 'finder\\shortcuts'
        }

    def start_scan(self):
        with self.lock:
            if self.is_scanning:
                return
            self.is_scanning = True
            self.is_finished = False
            self.is_stopped = False
            self.start_time = time.time()
            self.elapsed_time = 0
            self.total_dirs_scanned = 0
            self.total_files_scanned = 0
            self.total_bytes_scanned = 0
            self.current_folder = self.root_drive
            self.files = []
            self.category_stats = {cat: {'count': 0, 'bytes': 0} for cat in CATEGORIES}

        thread = threading.Thread(target=self._scan_worker, daemon=True)
        thread.start()

    def stop_scan(self):
        with self.lock:
            self.is_stopped = True

    def _scan_worker(self):
        queue = deque([self.root_drive])
        batch_files = []
        last_progress_time = time.time()

        while queue and not self.is_stopped:
            current_dir = queue.popleft()
            self.current_folder = current_dir
            self.total_dirs_scanned += 1

            try:
                with os.scandir(current_dir) as it:
                    for entry in it:
                        if self.is_stopped:
                            break
                        try:
                            # Skip junction points and symlinks
                            if entry.is_symlink():
                                continue

                            if entry.is_dir(follow_symlinks=False):
                                name_lower = entry.name.lower()
                                full_lower = entry.path.lower()
                                
                                # Skip blacklisted or hidden system roots
                                if name_lower in self.skip_dirs or any(s in full_lower for s in self.skip_dirs):
                                    continue
                                if name_lower.startswith('$') and name_lower not in {'$winreagent'}:
                                    continue

                                queue.append(entry.path)

                            elif entry.is_file(follow_symlinks=False):
                                self.total_files_scanned += 1
                                try:
                                    stat = entry.stat(follow_symlinks=False)
                                    size = stat.st_size
                                    self.total_bytes_scanned += size

                                    if size >= self.min_size_bytes:
                                        cat, ext = get_category_for_file(entry.name)
                                        mtime = stat.st_mtime
                                        batch_files.append({
                                            'path': entry.path,
                                            'name': entry.name,
                                            'size': size,
                                            'size_str': format_size(size),
                                            'category': cat,
                                            'ext': ext or '(none)',
                                            'mtime': mtime,
                                            'mtime_str': time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))
                                        })
                                        self.category_stats[cat]['count'] += 1
                                        self.category_stats[cat]['bytes'] += size
                                except OSError:
                                    pass
                        except OSError:
                            pass
            except (PermissionError, FileNotFoundError, OSError):
                pass

            now = time.time()
            if batch_files and (now - last_progress_time > 0.2):
                with self.lock:
                    self.files.extend(batch_files)
                    batch_files = []
                    self.elapsed_time = now - self.start_time
                last_progress_time = now

        # Flush any remaining files
        with self.lock:
            if batch_files:
                self.files.extend(batch_files)
            # Sort files descending by size
            self.files.sort(key=lambda x: x['size'], reverse=True)
            self.is_scanning = False
            self.is_finished = True
            self.elapsed_time = time.time() - self.start_time

    def get_status(self):
        with self.lock:
            current_elapsed = time.time() - self.start_time if self.is_scanning else self.elapsed_time
            return {
                'is_scanning': self.is_scanning,
                'is_finished': self.is_finished,
                'elapsed_seconds': round(current_elapsed, 1),
                'dirs_scanned': self.total_dirs_scanned,
                'files_scanned': self.total_files_scanned,
                'total_bytes_scanned': self.total_bytes_scanned,
                'total_bytes_str': format_size(self.total_bytes_scanned),
                'large_files_count': len(self.files),
                'current_folder': self.current_folder,
                'category_stats': {
                    cat: {
                        'count': self.category_stats[cat]['count'],
                        'bytes': self.category_stats[cat]['bytes'],
                        'bytes_str': format_size(self.category_stats[cat]['bytes']),
                        'name': CATEGORIES[cat]['name'],
                        'icon': CATEGORIES[cat]['icon']
                    }
                    for cat in CATEGORIES
                }
            }

    def query_files(self, category='all', min_size_mb=0, search='', limit=200, offset=0, sort_by='size_desc'):
        with self.lock:
            filtered = self.files

            # Filter by category
            if category and category != 'all':
                filtered = [f for f in filtered if f['category'] == category]

            # Filter by min size
            if min_size_mb > 0:
                min_bytes = min_size_mb * 1024 * 1024
                filtered = [f for f in filtered if f['size'] >= min_bytes]

            # Filter by search term
            if search:
                s_lower = search.strip().lower()
                filtered = [f for f in filtered if s_lower in f['name'].lower() or s_lower in f['path'].lower()]

            total_matches = len(filtered)

            # Sort
            if sort_by == 'size_asc':
                filtered = sorted(filtered, key=lambda x: x['size'])
            elif sort_by == 'name_asc':
                filtered = sorted(filtered, key=lambda x: x['name'].lower())
            elif sort_by == 'date_desc':
                filtered = sorted(filtered, key=lambda x: x['mtime'], reverse=True)
            # Default is size_desc, already sorted

            page = filtered[offset:offset+limit]
            return {
                'total_matches': total_matches,
                'offset': offset,
                'limit': limit,
                'files': page
            }

    def remove_file_record(self, file_path):
        """Remove a file from the list after it is deleted."""
        with self.lock:
            target = os.path.normpath(file_path).lower()
            idx_to_remove = None
            for idx, f in enumerate(self.files):
                if os.path.normpath(f['path']).lower() == target:
                    idx_to_remove = idx
                    break
            if idx_to_remove is not None:
                removed = self.files.pop(idx_to_remove)
                cat = removed['category']
                self.category_stats[cat]['count'] = max(0, self.category_stats[cat]['count'] - 1)
                self.category_stats[cat]['bytes'] = max(0, self.category_stats[cat]['bytes'] - removed['size'])
                return True
            return False
