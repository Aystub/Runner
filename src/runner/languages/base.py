import os
import time
import shutil
import asyncio

RUNNER_DIR = os.path.expanduser("~/.runner")
TEMP_DIR = os.path.join(RUNNER_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

def load_env_file(filepath):
    variables = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        variables[key.strip()] = val.strip().strip('"').strip("'")
        except Exception:
            pass
    return variables

def get_runner_env():
    env_vars = {}
    # 1. Global config env
    global_env = os.path.join(RUNNER_DIR, ".env")
    env_vars.update(load_env_file(global_env))
    
    # 2. Project source root env (for development/clones)
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    project_env = os.path.join(proj_root, ".env")
    env_vars.update(load_env_file(project_env))
    
    # 3. Current working directory env
    cwd_env = os.path.join(os.getcwd(), ".env")
    env_vars.update(load_env_file(cwd_env))
    
    # 4. System env overrides or supplements
    system_env = os.environ.copy()
    env_vars = {**env_vars, **system_env}
    return env_vars

def resolve_executable(name):
    env = get_runner_env()
    env_keys = {
        "node": "RUNNER_NODE_PATH",
        "go": "RUNNER_GO_PATH",
        "kotlinc": "RUNNER_KOTLINC_PATH",
        "java": "RUNNER_JAVA_PATH",
        "python3": "RUNNER_PYTHON3_PATH"
    }
    
    key = env_keys.get(name)
    if key and key in env:
        path = env[key]
        if path:
            expanded_path = os.path.expandvars(os.path.expanduser(path))
            if os.path.exists(expanded_path) and os.access(expanded_path, os.X_OK):
                return expanded_path
            
    system_path = shutil.which(name)
    if system_path:
        return system_path
    return name


def is_executable_available(name):
    path = resolve_executable(name)
    if os.path.exists(path) and os.access(path, os.X_OK):
        return True
    system_path = shutil.which(path)
    if system_path:
        return True
    return False

async def run_subprocess(cmd, cwd=None):
    start_time = time.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=get_runner_env()
        )
        stdout, stderr = await proc.communicate()
        elapsed_time = (time.time() - start_time) * 1000
        output = stdout.decode('utf-8', errors='replace') + stderr.decode('utf-8', errors='replace')
        return output, elapsed_time, proc.returncode
    except Exception as e:
        elapsed_time = (time.time() - start_time) * 1000
        return f"Failed to execute command: {' '.join(cmd)}\nError: {str(e)}\n", elapsed_time, -1

class ClassProperty:
    def __init__(self, func):
        self.func = func
    def __get__(self, instance, owner):
        return self.func(owner)

class BaseLanguage:
    name: str = ""              # e.g., "python"
    display_name: str = ""      # e.g., "Python 🐍"
    editor_language: str = ""   # e.g., "python" (for syntax highlighting)
    extension: str = ""         # e.g., "py"
    template_file: str = ""     # e.g., "template.py"
    executables: list[str] = [] # list of executables required, e.g. ["python3"]
    install_instructions: dict[str, str] = {} # instructions to install, e.g. {"macos": "brew install...", "linux": "apt install..."}



    
    @ClassProperty
    def template(cls) -> str:
        import sys
        if not cls.template_file:
            return ""
        module = sys.modules[cls.__module__]
        if hasattr(module, "__file__") and module.__file__:
            dir_path = os.path.dirname(module.__file__)
            template_path = os.path.join(dir_path, cls.template_file)
            if os.path.exists(template_path):
                try:
                    with open(template_path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass
        return ""
    
    @classmethod
    def is_available(cls) -> bool:
        if not cls.executables:
            return False
        return all(is_executable_available(exe) for exe in cls.executables)

    @classmethod
    async def get_version(cls) -> str:
        """Return version string or 'unknown'"""
        return "unknown"

    @classmethod
    async def run(cls, code: str) -> tuple[str, float, int]:
        """Run the code and return (output, elapsed_ms, exit_code)"""
        raise NotImplementedError
