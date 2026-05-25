"""
Vox File Module
Handles file operations: copy, move, delete, search, create
"""
import os
import shutil
import glob
from pathlib import Path
from typing import List, Optional, Tuple
import re
import config

class FileManager:
    def __init__(self):
        self.home_dir = Path.home()
        self.common_paths = {
            'desktop': self.home_dir / 'Desktop',
            'downloads': self.home_dir / 'Downloads',
            'documents': self.home_dir / 'Documents',
            'pictures': self.home_dir / 'Pictures',
            'music': self.home_dir / 'Music',
            'videos': self.home_dir / 'Videos'
        }

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve path string to absolute Path"""
        # Check if it's a common location
        path_lower = path_str.lower().strip()

        if path_lower in self.common_paths:
            return self.common_paths[path_lower]

        # Handle tilde expansion
        if path_str.startswith('~'):
            path_str = os.path.expanduser(path_str)

        # Handle relative paths
        path = Path(path_str)
        if not path.is_absolute():
            path = Path.cwd() / path

        return path.resolve()

    def copy_file(self, source: str, destination: str) -> Tuple[bool, str]:
        """Copy file or directory"""
        try:
            src_path = self._resolve_path(source)
            dst_path = self._resolve_path(destination)

            if not src_path.exists():
                return False, f"Source not found: {source}"

            # If destination is a directory, copy into it
            if dst_path.is_dir():
                dst_path = dst_path / src_path.name

            if src_path.is_file():
                shutil.copy2(src_path, dst_path)
                return True, f"Copied file to {dst_path}"
            elif src_path.is_dir():
                shutil.copytree(src_path, dst_path)
                return True, f"Copied folder to {dst_path}"

        except Exception as e:
            return False, f"Error copying: {str(e)}"

    def move_file(self, source: str, destination: str) -> Tuple[bool, str]:
        """Move file or directory"""
        try:
            src_path = self._resolve_path(source)
            dst_path = self._resolve_path(destination)

            if not src_path.exists():
                return False, f"Source not found: {source}"

            # If destination is a directory, move into it
            if dst_path.is_dir():
                dst_path = dst_path / src_path.name

            shutil.move(str(src_path), str(dst_path))
            return True, f"Moved to {dst_path}"

        except Exception as e:
            return False, f"Error moving: {str(e)}"

    def delete_file(self, path: str, confirm: bool = True) -> Tuple[bool, str]:
        """Professional robust deletion for Windows (handles read-only & locks)"""
        import stat
        
        def _remove_readonly(func, path, _):
            """Clear read-only bit and retry deletion"""
            os.chmod(path, stat.S_IWRITE)
            func(path)

        try:
            target_path = self._resolve_path(path)

            if not target_path.exists():
                return False, f"Not found: {path}"

            if confirm:
                print(f"⚠️  Deleting: {target_path}")

            if target_path.is_file():
                try:
                    target_path.unlink()
                except PermissionError:
                    os.chmod(target_path, stat.S_IWRITE)
                    target_path.unlink()
                return True, f"Deleted file: {target_path.name}"
            
            elif target_path.is_dir():
                # Use onerror handler to fix read-only files inside the folder
                shutil.rmtree(target_path, onerror=_remove_readonly)
                return True, f"Deleted folder: {target_path.name}"

        except Exception as e:
            # If still fails, it might be open in another program
            err_msg = str(e)
            if "Access is denied" in err_msg:
                return False, "Access denied. Please close any files inside that folder and try again."
            return False, f"Error deleting: {err_msg}"

    def search_file(self, filename: str) -> str:
        """Professional optimized search: Prioritizes common folders for speed."""
        try:
            name = filename.lower().strip()
            
            # 1. Search in priority areas (Very Fast)
            priority_dirs = [
                self.common_paths['desktop'],
                self.common_paths['documents'],
                self.common_paths['downloads'],
                Path.cwd()
            ]

            results = []
            for d in priority_dirs:
                if not d.exists(): continue
                # Look for exact or partial matches
                for item in d.rglob('*'):
                    if name in item.name.lower():
                        results.append(item)
                        if len(results) >= 5: break # Fast enough
                if results: break

            if not results:
                # 2. Broader search in Home (Slower)
                for item in self.home_dir.glob(f"*{name}*"):
                    results.append(item)

            if results:
                top = results[0]
                # If it's a file, offer to open it
                os.startfile(top)
                return f"I found '{top.name}' at {top.parent}. Opening it now."
            
            return f"I couldn't find any file named '{filename}' in your common folders."

        except Exception as e:
            return f"File search error: {e}"

    def create_folder(self, path: str) -> Tuple[bool, str]:
        """Create new folder"""
        try:
            folder_path = self._resolve_path(path)
            folder_path.mkdir(parents=True, exist_ok=True)
            return True, f"Created folder: {folder_path}"
        except Exception as e:
            return False, f"Error creating folder: {str(e)}"

    def create_file(self, path: str, content: str = "") -> Tuple[bool, str]:
        """Create new file"""
        try:
            file_path = self._resolve_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True, f"Created file: {file_path}"
        except Exception as e:
            return False, f"Error creating file: {str(e)}"

    def open_file(self, path: str) -> Tuple[bool, str]:
        """Open file with default application"""
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                return False, f"File not found: {path}"

            import os
            os.startfile(file_path)
            return True, f"Opening {file_path.name}"

        except Exception as e:
            return False, f"Error opening file: {str(e)}"

    def rename_file(self, old_name: str, new_name: str) -> Tuple[bool, str]:
        """Rename file or folder"""
        try:
            old_path = self._resolve_path(old_name)
            new_path = old_path.parent / new_name

            old_path.rename(new_path)
            return True, f"Renamed to {new_name}"

        except Exception as e:
            return False, f"Error renaming: {str(e)}"

    def get_file_info(self, path: str) -> dict:
        """Get file information"""
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                return {}

            stat = file_path.stat()

            return {
                'name': file_path.name,
                'path': str(file_path),
                'size': stat.st_size,
                'size_human': self._format_size(stat.st_size),
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'is_file': file_path.is_file(),
                'is_dir': file_path.is_dir(),
                'extension': file_path.suffix
            }

        except Exception as e:
            print(f"❌ Error getting file info: {e}")
            return {}

    def _format_size(self, size_bytes: int) -> str:
        """Format file size to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def list_directory(self, path: str = None) -> List[dict]:
        """List contents of directory"""
        try:
            if path:
                dir_path = self._resolve_path(path)
            else:
                dir_path = Path.cwd()

            items = []
            for item in dir_path.iterdir():
                items.append({
                    'name': item.name,
                    'type': 'folder' if item.is_dir() else 'file',
                    'path': str(item)
                })

            return sorted(items, key=lambda x: (x['type'] != 'folder', x['name'].lower()))

        except Exception as e:
            print(f"❌ Error listing directory: {e}")
            return []

# Test
if __name__ == "__main__":
    fm = FileManager()

    # Test operations
    print("Testing File Manager...")

    # Create test folder
    success, msg = fm.create_folder("~/Desktop/Vox_Test")
    print(msg)

    # Create test file
    success, msg = fm.create_file("~/Desktop/Vox_Test/hello.txt", "Hello from Vox!")
    print(msg)

    # Search for files
    results = fm.search_files("*.txt", "~/Desktop")
    print(f"Found {len(results)} .txt files")


