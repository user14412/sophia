from config import RESOURCES_DIR
import os

ref_chapter_local_path = str(RESOURCES_DIR / "documents" / "static" / "lecture01.txt")

print(os.path.basename(ref_chapter_local_path))