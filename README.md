# ⚡ Runner: Terminal-Based Code Playground

A terminal-based TUI (Textual User Interface) playground for quickly running code snippets. It supports:
- Python 
- JavaScript (Node.js)
- Go
- Kotlin

Easy to add support for new languages.

<p align="center">
  <img src=".github/art/RunnderDemo.gif" width="100%" />
</p>

---

## ⚙️ Getting Started

### Homebrew
```bash
brew install runner
```

Run Runner:
```bash
runner
```

## Manual Installation
1. **Python 3.8+**
2. **Install the package**: Install the package along with its dependencies (like Textual) in editable development mode:
   ```bash
   pip install -e .
   ```
3. (Optional) Runtimes for languages you wish to run:
   - Node.js (for JavaScript)
   - Go toolchain (for Go)
   - Kotlin compiler & Java Runtime (for Kotlin)

#### Runtime Path Configuration (`.env`)
By default, `runner` searches your system `PATH` to resolve compiler paths. If you have runtimes installed in custom paths (e.g., via `pyenv`, `nvm`, or Homebrew), copy `.env.example` to `.env` and fill in the absolute paths. You can use standard home directory shorthands (`~`) or environment variables in these paths:
```env
RUNNER_PYTHON3_PATH=~/.pyenv/shims/python3
RUNNER_NODE_PATH=~/.nvm/versions/node/v18.0.0/bin/node
RUNNER_GO_PATH=/usr/local/go/bin/go
RUNNER_KOTLINC_PATH=/opt/kotlin/bin/kotlinc
RUNNER_JAVA_PATH=/opt/java/bin/java
```
*Note: `runner` will load configuration files from `~/.runner/.env`, the current working directory `.env`, or the project root `.env`.*

#### Running the App
You can run `runner` using any of the following methods:

* **As an installed package** (after running `pip install .` or `pip install -e .`):
  ```bash
  runner
  ```
* **Using the launcher script** (directly from the repository root):
  ```bash
  ./runner
  ```
* **Directly via Python module execution**:
  ```bash
  python3 -m runner
  ```

---

## 🧩 Adding a New Language
The application is designed to automatically register new languages. To add support for a new language (e.g. `rust`):

1. Create a new folder under `src/runner/languages/` (e.g., `src/runner/languages/rust/`).
2. Add your native starting template code to `src/runner/languages/rust/template.rs`.
3. Create `src/runner/languages/rust/runner.py` defining a subclass of `BaseLanguage`:
   ```python
   from ..base import BaseLanguage, resolve_executable, run_subprocess

   class RustLanguage(BaseLanguage):
       name = "rust"
       display_name = "Rust 🦀"
       editor_language = "rust"  # Syntax highlighting spec
       extension = "rs"
       template_file = "template.rs"
       executables = ["rustc", "cargo"]  # Required system binaries
       install_instructions = {
           "macos": "brew install rustup-init",
           "linux": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
           "web": "https://www.rust-lang.org/tools/install"
       }

       @classmethod
       async def get_version(cls) -> str:
           # Execute 'rustc --version' and parse it
           cmd = [resolve_executable("rustc"), "--version"]
           output, _, code = await run_subprocess(cmd)
           if code == 0:
               return output.strip().split()[1]
           return "unknown"


       @classmethod
       async def run(cls, code: str) -> tuple[str, float, int]:
           # Write code to temp file, compile and execute it
           ...
   ```

Upon launching the app, the discovery module will automatically import the new package, sort it alphabetically, load the native template, and enforce path/binary checks before running.
