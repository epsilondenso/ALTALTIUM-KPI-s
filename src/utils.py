from pathlib import Path

def get_files(dir: str|Path):
    files_list = [file.name for file in dir.iterdir() if file.is_file()] 
    return files_list