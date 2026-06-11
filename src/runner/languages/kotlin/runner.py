from ..base import BaseLanguage, resolve_executable, run_subprocess, TEMP_DIR
import os
import re

class KotlinLanguage(BaseLanguage):
    name = "kotlin"
    display_name = "Kotlin 💜"
    editor_language = "java"  # Textual highlighting fallback
    extension = "kt"
    template_file = "template.kt"
    executables = ["kotlinc", "java"]
    install_instructions = {
        "macos": "brew install kotlin",
        "linux": "sudo apt-get install kotlin",
        "web": "https://kotlinlang.org/docs/command-line.html"
    }


    @classmethod
    def clean_comments(cls, code):
        pattern = re.compile(
            r'(?P<comment>//.*?$|/\*.*?\*/)|(?P<string>"(?:\\.|[^"\\])*"|`[^`]*`|\'(?:\\.|[^\'\\])*\')',
            re.MULTILINE | re.DOTALL
        )
        def replacer(match):
            if match.group('comment'):
                return ''
            return match.group('string')
        return pattern.sub(replacer, code)

    @classmethod
    def has_kotlin_main(cls, code):
        clean = cls.clean_comments(code)
        return bool(re.search(r'\bfun\s+main\b', clean))

    @classmethod
    async def get_version(cls) -> str:
        cmd = [resolve_executable("kotlinc"), "-version"]
        output, _, code = await run_subprocess(cmd)
        if code == 0:
            parts = output.strip().split()
            for i, p in enumerate(parts):
                if p == "kotlinc-jvm" and i + 1 < len(parts):
                    return parts[i + 1]
        return "unknown"

    @classmethod
    async def run(cls, code: str) -> tuple[str, float, int]:
        wrapped_code = code
        if not cls.has_kotlin_main(code):
            wrapped_code = f"""fun main() {{
{code}
}}
"""
        import tempfile
        fd_kt, kt_path = tempfile.mkstemp(suffix=".kt", dir=TEMP_DIR)
        jar_path = kt_path + ".jar"
        try:
            with os.fdopen(fd_kt, "w", encoding="utf-8") as f:
                f.write(wrapped_code)
                
            kotlinc_cmd = [resolve_executable("kotlinc"), kt_path, "-include-runtime", "-d", jar_path]
            compile_output, compile_time, compile_code = await run_subprocess(kotlinc_cmd)
            if compile_code != 0:
                return f"--- COMPILATION FAILED ---\n{compile_output}", compile_time, compile_code
                
            java_cmd = [resolve_executable("java"), "-jar", jar_path]
            run_output, run_time, run_code = await run_subprocess(java_cmd)
            return run_output, compile_time + run_time, run_code
        finally:
            for path in (kt_path, jar_path):
                try:
                    os.remove(path)
                except Exception:
                    pass

