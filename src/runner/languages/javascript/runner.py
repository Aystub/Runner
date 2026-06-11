from ..base import BaseLanguage, resolve_executable, run_subprocess, TEMP_DIR
import os

class JavaScriptLanguage(BaseLanguage):
    name = "javascript"
    display_name = "JavaScript 🟨"
    editor_language = "javascript"
    extension = "js"
    template_file = "template.js"
    executables = ["node"]
    install_instructions = {
        "macos": "brew install node",
        "linux": "sudo apt-get install nodejs npm",
        "web": "https://nodejs.org/"
    }


    @classmethod
    async def get_version(cls) -> str:
        cmd = [resolve_executable("node"), "--version"]
        output, _, code = await run_subprocess(cmd)
        if code == 0:
            return output.strip().lstrip("v")
        return "unknown"

    @classmethod
    async def run(cls, code: str) -> tuple[str, float, int]:
        import tempfile
        fd, temp_path = tempfile.mkstemp(suffix=".js", dir=TEMP_DIR)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code)
            cmd = [resolve_executable("node"), temp_path]
            return await run_subprocess(cmd)
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass

