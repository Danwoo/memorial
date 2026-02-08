import os
import shutil

BASE_DIR = r"C:\Users\danny\OneDrive\Desktop\code\1month1project\memorial\backend"
CORE_DIR = os.path.join(BASE_DIR, "app", "core")
CONFIG_DIR = os.path.join(BASE_DIR, "app", "config")

def move_files():
    if not os.path.exists(CONFIG_DIR):
        print(f"Creating {CONFIG_DIR}")
        os.makedirs(CONFIG_DIR)
    
    if os.path.exists(CORE_DIR):
        print(f"Moving files from {CORE_DIR} to {CONFIG_DIR}")
        for filename in os.listdir(CORE_DIR):
            if filename == "__pycache__":
                continue
                
            src = os.path.join(CORE_DIR, filename)
            dst = os.path.join(CONFIG_DIR, filename)
            
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                print(f"Copied {filename}")
        
        # Remove core dir
        # shutil.rmtree(CORE_DIR) 
        # print("Removed core directory")
    else:
        print("Core directory does not exist (maybe already moved?)")

if __name__ == "__main__":
    move_files()
