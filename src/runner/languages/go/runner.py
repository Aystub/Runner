from ..base import BaseLanguage, resolve_executable, run_subprocess, TEMP_DIR
import os
import re

class GoLanguage(BaseLanguage):
    name = "go"
    display_name = "Go 🔵"
    editor_language = "go"
    extension = "go"
    template_file = "template.go"
    executables = ["go"]
    install_instructions = {
        "macos": "brew install go",
        "linux": "sudo apt-get install golang-go",
        "web": "https://go.dev/doc/install"
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
    def has_go_main(cls, code):
        clean = cls.clean_comments(code)
        return bool(re.search(r'\bpackage\s+main\b', clean))

    @classmethod
    async def get_version(cls) -> str:
        cmd = [resolve_executable("go"), "version"]
        output, _, code = await run_subprocess(cmd)
        if code == 0:
            parts = output.strip().split()
            for p in parts:
                if p.startswith("go1."):
                    return p.lstrip("go")
        return "unknown"

    @classmethod
    async def run(cls, code: str) -> tuple[str, float, int]:
        wrapped_code = code
        if not cls.has_go_main(code):
            wrapped_code = f"""package main

import (
	"fmt"
	"math"
	"strings"
	"time"
)

func main() {{
	_ = fmt.Println
	_ = math.Abs
	_ = strings.ToLower
	_ = time.Now

{code}
}}
"""
        import tempfile
        fd, temp_path = tempfile.mkstemp(suffix=".go", dir=TEMP_DIR)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(wrapped_code)
            cmd = [resolve_executable("go"), "run", temp_path]
            return await run_subprocess(cmd)
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass

