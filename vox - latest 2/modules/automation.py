import os
import tempfile
import shutil

class PCAutomation:
    def clean_temp_files(self) -> str:
        temp_dir = tempfile.gettempdir()
        count = 0
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            try:
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                count += 1
            except Exception:
                pass
        return f"Cleaned {count} temporary files from your system."

    def open_folder(self, folder_name: str) -> str:
        # Clean name: "downloads folder" -> "downloads"
        name = folder_name.lower().replace("folder", "").strip()
        
        # Standard Windows Paths
        user_profile = os.environ.get('USERPROFILE', os.path.expanduser("~"))
        paths = {
            "downloads": os.path.join(user_profile, "Downloads"),
            "documents": os.path.join(user_profile, "Documents"),
            "desktop": os.path.join(user_profile, "Desktop"),
            "pictures": os.path.join(user_profile, "Pictures"),
            "music": os.path.join(user_profile, "Music"),
            "videos": os.path.join(user_profile, "Videos"),
        }
        
        target_path = paths.get(name)
        if target_path and os.path.exists(target_path):
            os.startfile(target_path)
            return f"Opening your {name.capitalize()} folder."
            
        # Try direct opening if path was passed
        if os.path.exists(folder_name):
            os.startfile(folder_name)
            return f"Opening folder: {folder_name}"

        return f"I could not find the {name} folder."