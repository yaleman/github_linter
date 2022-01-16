""" utility functions """

from pathlib import Path

def get_fix_file_path(category: str, filename: str) -> Path:
    """ gets a Path object for a filename within the fixes dir for the given category """
    module_parent = Path(__file__).parent
    fixes_path = module_parent / f"fixes/{category}/{filename}"
    if not fixes_path.exists():
        base_filename = Path(filename).name
        fixes_path = module_parent / f"fixes/{category}/{base_filename}"
    return fixes_path
