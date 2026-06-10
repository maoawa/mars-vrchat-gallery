#!/usr/bin/env python3
import os
import re
from pathlib import Path

def rename_screenshots(directory="."):
    """
    Batch rename VRChat screenshots by removing milliseconds and resolution.
    Example: VRChat_2026-06-04_22-35-28.329_3840x2160.png -> VRChat_2026-06-04_22-35-28.png
    """
    directory = Path(directory)
    
    # Pattern: VRChat_YYYY-MM-DD_HH-MM-SS.milliseconds_WIDTHxHEIGHT.png
    pattern = r"(VRChat_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.\d+_\d+x\d+\.png$"
    
    renamed_count = 0
    for file_path in directory.glob("VRChat_*.png"):
        filename = file_path.name
        
        match = re.match(pattern, filename)
        if match:
            new_name = match.group(1) + ".png"
            new_path = file_path.parent / new_name
            
            if new_path.exists():
                print(f"⚠️  Skipped (already exists): {filename} -> {new_name}")
            else:
                file_path.rename(new_path)
                print(f"✓ Renamed: {filename} -> {new_name}")
                renamed_count += 1
        else:
            print(f"⊘ Skipped (doesn't match pattern): {filename}")
    
    print(f"\nTotal renamed: {renamed_count}")

if __name__ == "__main__":
    rename_screenshots()
