#!/usr/bin/env python3
import os
from pathlib import Path
from PIL import Image

def resize_screenshots(source_dir=".", output_dir="thumbnails"):
    """
    Batch resize VRChat screenshots to 720p:
    - Landscape: height = 720, width scales proportionally
    - Vertical: width = 720, height scales proportionally
    """
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    
    # Create thumbnail directory if it doesn't exist
    output_path.mkdir(exist_ok=True)
    
    resized_count = 0
    
    for file_path in sorted(source_path.glob("VRChat_*.png")):
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                
                # Determine orientation and calculate new size
                if width > height:
                    # Landscape: height = 720, width scales proportionally
                    new_height = 720
                    new_width = int(width * (720 / height))
                    new_size = (new_width, new_height)
                    orientation = "landscape"
                else:
                    # Vertical: width = 720, height scales proportionally
                    new_width = 720
                    new_height = int(height * (720 / width))
                    new_size = (new_width, new_height)
                    orientation = "vertical"
                
                # Resize image
                resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Save to thumbnail folder
                output_file = output_path / file_path.name
                resized_img.save(output_file, "PNG", quality=95)
                
                print(f"✓ Resized ({orientation} {width}x{height} -> {new_size[0]}x{new_size[1]}): {file_path.name}")
                resized_count += 1
                
        except Exception as e:
            print(f"✗ Error processing {file_path.name}: {e}")
    
    print(f"\nTotal resized: {resized_count}")
    print(f"Output folder: {output_path.absolute()}")

if __name__ == "__main__":
    resize_screenshots()
