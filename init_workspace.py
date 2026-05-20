import os

def init_structure(base_path):
    subdirs = [
        'scripts',
        'references',
        'assets',
        'output'
    ]
    for subdir in subdirs:
        path = os.path.join(base_path, subdir)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Created: {path}")
        else:
            print(f"Exists: {path}")

if __name__ == "__main__":
    # 使用當前目錄作為根目錄
    init_structure('.')
