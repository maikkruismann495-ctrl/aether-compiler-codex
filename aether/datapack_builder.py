# aether/datapack_builder.py

import os
import json
import re
import shutil
from typing import Dict, List, Optional

class DatapackBuilder:
    """
    Writes the Intermediate Representation (IR) to disk as a valid 
    Minecraft Java Edition 1.21.11 datapack.
    """
    PACK_FORMAT = [94, 1]
    PACK_DESC = "Compiled from Aether v3.0"
    NS_RE = re.compile(r"^[a-z0-9_\-\.]+$")

    def __init__(self, ir: Dict[str, List[str]], out_dir: str, root_ns: str = "aether", manual_data_dir: Optional[str] = None):
        self.ir = ir
        self.out_dir = out_dir
        self.root_ns = root_ns
        # Path to the user's manual data folder (if they have one)
        self.manual_data_dir = manual_data_dir

    def build(self):
        # 1. Create the base datapack structure
        os.makedirs(self.out_dir, exist_ok=True)
        
        # Write pack.mcmeta
        with open(os.path.join(self.out_dir, "pack.mcmeta"), "w") as f:
            json.dump({"pack": {"pack_format": self.PACK_FORMAT, "description": self.PACK_DESC}}, f, indent=4)
        
        data_dir = os.path.join(self.out_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        # 2. Write compiled Aether functions and tags
        for f, cmds in self.ir.items():
            if "load.json" in f or "tick.json" in f:
                tag_dir = os.path.join(data_dir, "minecraft", "tags", "function")
                os.makedirs(tag_dir, exist_ok=True)
                filename = f.split("/")[-1]
                with open(os.path.join(tag_dir, filename), "w") as file:
                    json.dump({"values": cmds}, file, indent=4)
            else:
                ns, path = f.split(":", 1)
                if not self.NS_RE.match(ns): raise ValueError(f"Invalid namespace '{ns}'")
                ns_dir = os.path.join(data_dir, ns, "function")
                os.makedirs(ns_dir, exist_ok=True)
                fp = os.path.join(ns_dir, path.replace("/", "_") + ".mcfunction")
                with open(fp, "w") as file:
                    for c in cmds: file.write(c.strip() + "\n")
                    
        # 3. MERGE MANUAL DATA (Recipes, Dimensions, Advancements, etc.)
        # If the user has a 'data' folder in their project, it gets merged perfectly!
        if self.manual_data_dir and os.path.isdir(self.manual_data_dir):
            for item in os.listdir(self.manual_data_dir):
                src_path = os.path.join(self.manual_data_dir, item)
                dest_path = os.path.join(data_dir, item)
                
                # If it's a directory (like a namespace folder), merge it
                if os.path.isdir(src_path):
                    # dirs_exist_ok=True allows us to merge into folders Aether already created!
                    shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                else:
                    # If it's a loose file, just copy it
                    shutil.copy2(src_path, dest_path)