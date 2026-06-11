import os
import importlib
from .base import BaseLanguage

LANGUAGES = {}

def discover_languages():
    current_dir = os.path.dirname(__file__)
    # Dynamically scan and import all package submodules in sorted order
    for name in sorted(os.listdir(current_dir)):
        sub_dir = os.path.join(current_dir, name)
        if os.path.isdir(sub_dir):
            imported = False
            # Try importing runner.py first
            if os.path.exists(os.path.join(sub_dir, "runner.py")):
                try:
                    importlib.import_module(f"runner.languages.{name}.runner")
                    imported = True
                except Exception:
                    pass
            # Fallback to standard package import if runner wasn't loaded
            if not imported and os.path.exists(os.path.join(sub_dir, "__init__.py")):
                try:
                    importlib.import_module(f"runner.languages.{name}")
                except Exception:
                    pass

                
    # Populate the LANGUAGES map based on registered subclasses in sorted order
    # This guarantees that LANGUAGES.keys() is always deterministic and sorted alphabetically!
    subclasses = BaseLanguage.__subclasses__()
    valid_subclasses = [cls for cls in subclasses if cls.name]
    valid_subclasses.sort(key=lambda cls: cls.name)
    
    for cls in valid_subclasses:
        LANGUAGES[cls.name] = cls

discover_languages()
