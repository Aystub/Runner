from ..base import BaseLanguage, resolve_executable, run_subprocess, TEMP_DIR
import os

class PythonLanguage(BaseLanguage):
    name = "python"
    display_name = "Python 🐍"
    editor_language = "python"
    extension = "py"
    template_file = "template.py"
    executables = ["python3"]
    install_instructions = {
        "macos": "brew install python",
        "linux": "sudo apt-get install python3",
        "web": "https://www.python.org/downloads/"
    }


    @classmethod
    async def get_version(cls) -> str:
        cmd = [resolve_executable("python3"), "--version"]
        output, _, code = await run_subprocess(cmd)
        if code == 0:
            return output.strip().replace("Python ", "")
        return "unknown"

    @classmethod
    async def run(cls, code: str) -> tuple[str, float, int]:
        import tempfile
        fd, temp_path = tempfile.mkstemp(suffix=".py", dir=TEMP_DIR)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code)
            cmd = [resolve_executable("python3"), temp_path]
            return await run_subprocess(cmd)
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass

