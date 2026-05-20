import os

def init_skill_structure(base_path):
    """
    依照標準化規範初始化技能目錄結構 (ASCII Version)
    """
    sub_dirs = [
        'scripts',
        'references',
        'assets',
        'output'
    ]
    
    print(f"Starting skill directory initialization: {base_path}")
    
    for sub_dir in sub_dirs:
        target_path = os.path.join(base_path, sub_dir)
        if not os.path.exists(target_path):
            os.makedirs(target_path)
            print(f"  [OK] Created directory: {sub_dir}")
        else:
            print(f"  [SKIP] Directory already exists: {sub_dir}")

    # Create initial README.md
    readme_path = os.path.join(base_path, 'README.md')
    if not os.path.exists(readme_path):
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(f"# Green Market Registrar Skill\n\nInitialized structure.")
        print(f"  [OK] Created README.md")

if __name__ == "__main__":
    # Set skill root path
    skill_root = r"skills\green-market-regsitrar"
    # Note: I noticed a typo in my previous path 'regsitrar', 
    # I will use the correct one 'registrar' to match the existing folder
    skill_root_correct = r"skills\green-market-registrar"
    init_skill_structure(skill_root_correct)
    print("\nSkill structure initialization completed!")
