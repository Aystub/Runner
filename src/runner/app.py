import os
import sys
import json
import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static, TextArea, RichLog, OptionList
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding

from runner.languages import LANGUAGES


# ==============================================================================
# Constants & Directory Setup
# ==============================================================================
RUNNER_DIR = os.path.expanduser("~/.runner")
SESSIONS_DIR = os.path.join(RUNNER_DIR, "sessions")
TEMP_DIR = os.path.join(RUNNER_DIR, "temp")

os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

WELCOME_BANNER = """
 ██████╗ ██╗   ██╗███╗   ██╗███╗   ██╗███████╗██████╗ 
 ██╔══██╗██║   ██║████╗  ██║████╗  ██║██╔════╝██╔══██╗
 ██████╔╝██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██████╔╝
 ██╔══██╗██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██╔══██╗
 ██║  ██║╚██████╔╝██║ ╚████║██║ ╚████║███████╗██║  ██║
 ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
"""

TEMPLATES = {name: cls.template for name, cls in LANGUAGES.items()}

# ==============================================================================
# Session Management
# ==============================================================================
def list_sessions():
    sessions = []
    if not os.path.exists(SESSIONS_DIR):
        return sessions
    for filename in os.listdir(SESSIONS_DIR):
        if filename.startswith("session_") and filename.endswith(".json"):
            filepath = os.path.join(SESSIONS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "id" in data and "language" in data and "code" in data:
                        sessions.append(data)
            except Exception:
                pass
    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions

def save_session(session):
    session_id = session["id"]
    filepath = os.path.join(SESSIONS_DIR, f"session_{session_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2)

def load_session_by_id(session_id):
    filepath = os.path.join(SESSIONS_DIR, f"session_{session_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def delete_session(session_id):
    filepath = os.path.join(SESSIONS_DIR, f"session_{session_id}.json")
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass

# ==============================================================================
# Dynamic Code Running & Version Fetching
# ==============================================================================
async def run_code(language, code):
    if language in LANGUAGES:
        return await LANGUAGES[language].run(code)
    return f"Unsupported language: {language}", 0, -1

async def get_language_versions():
    tasks = []
    lang_keys = sorted(LANGUAGES.keys())
    for lkey in lang_keys:
        tasks.append(LANGUAGES[lkey].get_version())
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    versions = {}
    for i, lkey in enumerate(lang_keys):
        res = results[i]
        if isinstance(res, Exception):
            versions[lkey] = "unknown"
        else:
            versions[lkey] = res
    return versions

# ==============================================================================
# UI Screens
# ==============================================================================
class WelcomeScreen(Screen):
    BINDINGS = [
        Binding("delete", "delete_selected", "Delete", show=False),
        Binding("backspace", "delete_selected", "Delete"),
        Binding("d", "delete_selected", "Delete"),
        Binding("q", "quit_app", "Quit")
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="welcome_container"):
            yield Static(WELCOME_BANNER, id="welcome_banner")
            yield Static("Quick Code Runner & Playground", id="welcome_subtitle")
            yield Static("Select a session to resume, or start a new one:", id="welcome_prompt")
            yield OptionList(id="welcome_list")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_list()

    def refresh_list(self) -> None:
        option_list = self.query_one("#welcome_list")
        option_list.clear_options()
        
        self.sessions = list_sessions()
        
        # Option 0: Start New Session
        option_list.add_option("[+] Start New Session")
        
        # Historical sessions
        for s in self.sessions:
            lang_emoji = s["language"]
            if s["language"] in LANGUAGES:
                lang_emoji = LANGUAGES[s["language"]].display_name
                
            dt_str = s["updated_at"]
            try:
                dt = datetime.fromisoformat(dt_str)
                date_formatted = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_formatted = dt_str
                
            # Show the last line of actual code as snippet to bypass template comments/boilerplate
            lines = [line.strip() for line in s["code"].splitlines() if line.strip()]
            snippet = ""
            if lines:
                for line in reversed(lines):
                    if line not in ("}", "]", ")", "end", ""):
                        snippet = line[:35]
                        if len(line) > 35:
                            snippet += "..."
                        break
                if not snippet:
                    snippet = lines[-1][:35]
                    if len(lines[-1]) > 35:
                        snippet += "..."
                
            label = f"{lang_emoji:<12} | {date_formatted:<16} | {snippet}"
            option_list.add_option(label)
            
        # Option Last: Quit App
        option_list.add_option("[q] Quit App")
        option_list.highlighted = 0
        option_list.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        if idx == 0:
            self.app.switch_screen(LanguageSelectScreen())
        elif idx == len(self.sessions) + 1:
            self.app.exit()
        else:
            session = self.sessions[idx - 1]
            self.app.load_session(session["id"])

    def action_delete_selected(self) -> None:
        option_list = self.query_one("#welcome_list")
        idx = option_list.highlighted
        if idx is not None and 1 <= idx <= len(self.sessions):
            session_to_delete = self.sessions[idx - 1]
            delete_session(session_to_delete["id"])
            self.refresh_list()
            # Restore cursor position gracefully
            new_highlight = min(idx, len(self.sessions) + 1)
            option_list.highlighted = new_highlight

    def action_quit_app(self) -> None:
        self.app.exit()


class LanguageSelectScreen(Screen):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("q", "cancel", "Cancel")
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="lang_container"):
            yield Static("Select Language", id="lang_title")
            yield OptionList(id="lang_list")
        yield Footer()

    def on_mount(self) -> None:
        option_list = self.query_one("#lang_list")
        option_list.clear_options()
        
        # Add loading placeholders dynamically (check immediate availability first)
        for lang_name, lang_cls in sorted(LANGUAGES.items()):
            if not lang_cls.is_available():
                option_list.add_option(f"{lang_cls.display_name} (not installed ⚠️)")
            else:
                option_list.add_option(f"{lang_cls.display_name} (loading...)")
        option_list.add_option("[x] Cancel")
        option_list.highlighted = 0
        option_list.focus()
        
        # Spawn version checker in the background without blocking UI render
        self.run_worker(self.load_versions_async())

    async def load_versions_async(self) -> None:
        versions = await get_language_versions()
        
        # Safety check: if screen was dismissed, exit worker
        if self.app.screen is not self:
            return
            
        option_list = self.query_one("#lang_list")
        curr_highlighted = option_list.highlighted
        
        option_list.clear_options()
        for lang_name, lang_cls in sorted(LANGUAGES.items()):
            if not lang_cls.is_available():
                option_list.add_option(f"{lang_cls.display_name} (not installed ⚠️)")
            else:
                ver = versions.get(lang_name, "unknown")
                option_list.add_option(f"{lang_cls.display_name} (v{ver})")
        option_list.add_option("[x] Cancel")
        
        if curr_highlighted is not None:
            option_list.highlighted = curr_highlighted

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        # The cancel option is at index equal to the number of languages
        if idx == len(LANGUAGES):
            self.action_cancel()
            return
            
        langs = sorted(LANGUAGES.keys())
        selected_lang = langs[idx]
        lang_cls = LANGUAGES[selected_lang]
        if not lang_cls.is_available():
            self.app.switch_screen(LanguageInstallScreen(selected_lang))
        else:
            self.app.create_new_session(selected_lang)

    def action_cancel(self) -> None:
        self.app.switch_screen(WelcomeScreen())


class LanguageInstallScreen(Screen):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("q", "cancel", "Cancel")
    ]

    def __init__(self, lang_name, **kwargs):
        super().__init__(**kwargs)
        self.lang_name = lang_name
        self.lang_cls = LANGUAGES[lang_name]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="install_container"):
            yield Static(f"Missing {self.lang_cls.display_name} Runtime", id="install_title")
            yield Static("", id="install_desc")
            yield OptionList(id="install_list")
        yield Footer()

    def on_mount(self) -> None:
        self.update_diagnostics()

    def update_diagnostics(self, failed_recheck=False) -> None:
        # Build the executables checklist
        exe_list = []
        from runner.languages.base import is_executable_available
        for exe in self.lang_cls.executables:
            found = is_executable_available(exe)
            status = "[bold green]✓ Found[/bold green]" if found else "[bold red]✗ Missing[/bold red]"
            exe_list.append(f"  - {exe}: {status}")
        exe_checklist = "\n".join(exe_list)
        
        # Build installation suggestions
        instr = self.lang_cls.install_instructions
        suggestions = []
        if "macos" in instr:
            suggestions.append(f"  • macOS (Homebrew):     [bold cyan]{instr['macos']}[/bold cyan]")
        if "linux" in instr:
            suggestions.append(f"  • Linux (APT/Package):  [bold cyan]{instr['linux']}[/bold cyan]")
        if "web" in instr:
            suggestions.append(f"  • Official Website:     [underline]{instr['web']}[/underline]")
            
        suggestions_text = "\n".join(suggestions)
        
        prefix = "[bold red]✗ Verification Failed. Executables are still missing from PATH.[/bold red]\n\n" if failed_recheck else ""
        
        desc_text = (
            f"{prefix}"
            f"The required compilers/interpreters for [bold]{self.lang_cls.display_name}[/bold] are missing.\n\n"
            f"[bold white]Required Executables Checklist:[/bold white]\n{exe_checklist}\n\n"
            f"[bold white]Suggested Installation Instructions:[/bold white]\n{suggestions_text}\n\n"
            f"[yellow]💡 Tip: If installed in a custom path (e.g. via pyenv, nvm, sdkman),\n"
            f"configure it in your local .env file (e.g. RUNNER_{self.lang_cls.name.upper()}_PATH).[/yellow]"
        )
        
        desc = self.query_one("#install_desc")
        desc.update(desc_text)
        
        self.show_initial_menu()

    def show_initial_menu(self) -> None:
        option_list = self.query_one("#install_list")
        option_list.clear_options()
        
        # Check if actually available now (e.g., after a recheck)
        if self.lang_cls.is_available():
            option_list.add_option("[1] Start Session Now")
        else:
            option_list.add_option("[1] Recheck System (scan PATH)")
            option_list.add_option("[2] Start Session Anyway (ignore warnings)")
            
        option_list.add_option("[3] Back to Language Selection")
        option_list.highlighted = 0
        option_list.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        label = event.option.prompt
        
        if "Recheck System" in label:
            self.perform_recheck()
        elif "Start Session" in label:
            self.app.create_new_session(self.lang_name)
        elif "Back to Language Selection" in label:
            self.action_cancel()

    def perform_recheck(self) -> None:
        # Re-evaluate executables availability
        # We need to force reload environment variables to check new PATH or .env additions
        from runner.languages.base import get_runner_env
        get_runner_env()
        
        if self.lang_cls.is_available():
            desc_text = (
                f"[bold green]✓ System Verified![/bold green]\n\n"
                f"All required executables ({', '.join(self.lang_cls.executables)}) for [bold]{self.lang_cls.display_name}[/bold] were successfully found in your PATH or .env file.\n\n"
                f"You are ready to start code execution."
            )
            desc = self.query_one("#install_desc")
            desc.update(desc_text)
            
            option_list = self.query_one("#install_list")
            option_list.clear_options()
            option_list.add_option("[1] Start Session Now")
            option_list.add_option("[2] Back to Language Selection")
            option_list.highlighted = 0
            option_list.focus()
        else:
            self.update_diagnostics(failed_recheck=True)

    def action_cancel(self) -> None:
        self.app.switch_screen(LanguageSelectScreen())



class EditorHeader(Horizontal):
    def __init__(self, session, **kwargs):
        super().__init__(id="editor_header_panel", **kwargs)
        self.session = session
        self.status_text = "Idle"
        self.status_style = "green"

    def compose(self) -> ComposeResult:
        lang = self.session["language"]
        lang_emoji = LANGUAGES[lang].display_name if lang in LANGUAGES else lang
        yield Static(f"⚡ RUNNER | [bold white]{lang_emoji}[/bold white] | Session: {self.session['id']}", id="editor_header_title")
        yield Static(f"Status: [{self.status_style}]{self.status_text}[/{self.status_style}]", id="editor_header_status")

    def update_status(self, text, style="green") -> None:
        self.status_text = text
        self.status_style = style
        status_widget = self.query_one("#editor_header_status")
        status_widget.update(f"Status: [{style}]{text}[/{style}]")


class EditorScreen(Screen):
    BINDINGS = [
        ("ctrl+r", "run_code", "Run"),
        ("f5", "run_code", "Run"),
        ("escape", "exit_editor", "Exit"),
        ("ctrl+q", "exit_editor", "Exit"),
        ("ctrl+s", "save_session", "Save")
    ]

    def compose(self) -> ComposeResult:
        self.header = EditorHeader(self.app.current_session)
        yield self.header
        with Horizontal(id="main_area"):
            with Vertical(id="left_panel"):
                yield TextArea(
                    self.app.current_session["code"],
                    language=self.get_editor_language(self.app.current_session["language"]),
                    id="code_editor"
                )
            with Vertical(id="right_panel"):
                yield Static("OUTPUT PANEL", id="output_header")
                yield RichLog(id="output_log", highlight=True, markup=True)
        yield Footer()

    def get_editor_language(self, lang):
        if lang in LANGUAGES:
            return LANGUAGES[lang].editor_language
        return lang

    def on_mount(self) -> None:
        self.query_one("#code_editor").focus()
        self.query_one("#code_editor").show_line_numbers = True
        
        prev_output = self.app.current_session.get("output", "")
        if prev_output:
            log = self.query_one("#output_log")
            log.write(prev_output)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if self.app.current_session:
            self.app.current_session["code"] = event.text_area.text
            self.app.current_session["updated_at"] = datetime.now().isoformat()
            save_session(self.app.current_session)

    def action_save_session(self) -> None:
        if self.app.current_session:
            editor = self.query_one("#code_editor")
            self.app.current_session["code"] = editor.text
            self.app.current_session["updated_at"] = datetime.now().isoformat()
            save_session(self.app.current_session)
            self.header.update_status("Saved Session", "green")
            self.set_timer(1.5, lambda: self.header.update_status("Idle", "green"))

    async def action_run_code(self) -> None:
        if getattr(self, "_code_running", False):
            return
            
        self._code_running = True
        try:
            self.header.update_status("Running...", "yellow")
            
            editor = self.query_one("#code_editor")
            code_to_run = editor.text
            log = self.query_one("#output_log")
            log.clear()
            
            # Check availability before executing
            lang = self.app.current_session["language"]
            if lang in LANGUAGES and not LANGUAGES[lang].is_available():
                log.write("[bold red]Error: Runtime/compiler not found![/bold red]\n\n")
                log.write("The following required executables are missing from your system/PATH:\n")
                from languages.base import is_executable_available
                for exe in LANGUAGES[lang].executables:
                    status = "[bold green]✓ Found[/bold green]" if is_executable_available(exe) else "[bold red]✗ Missing[/bold red]"
                    log.write(f"  - {exe}: {status}\n")
                log.write("\n[yellow]Please install the required tools, add them to your PATH, or configure their paths in your local .env file.[/yellow]")
                self.header.update_status("Missing Runtime", "red")
                self._code_running = False
                return
                
            log.write("[bold yellow]Running code...[/bold yellow]\n")
            
            output, elapsed, exit_code = await run_code(self.app.current_session["language"], code_to_run)
            
            log.clear()
            log.write(output)
            
            if exit_code == 0:
                status_style = "green"
                status_text = "Success"
                log.write(f"\n[bold green]✓ Execution successful ({elapsed:.1f}ms)[/bold green]")
            else:
                status_style = "red"
                status_text = f"Failed (code {exit_code})"
                log.write(f"\n[bold red]✗ Execution failed ({elapsed:.1f}ms) with exit code {exit_code}[/bold red]")
                
            self.header.update_status(f"{status_text} ({elapsed:.1f}ms)", status_style)
            
            if self.app.current_session:
                self.app.current_session["output"] = output
                save_session(self.app.current_session)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            with open(os.path.expanduser("~/.runner/debug.log"), "a") as f:
                f.write(f"\n--- ERROR AT {datetime.now()} ---\n{tb}\n")
            try:
                log = self.query_one("#output_log")
                log.write(f"[bold red]INTERNAL TUI ERROR:[/bold red]\n{tb}")
            except:
                pass
            self.header.update_status("Internal Error", "red")
        finally:
            self._code_running = False

    def action_exit_editor(self) -> None:
        if self.app.current_session:
            editor = self.query_one("#code_editor")
            self.app.current_session["code"] = editor.text
            self.app.current_session["updated_at"] = datetime.now().isoformat()
            save_session(self.app.current_session)
            
        self.app.switch_screen(WelcomeScreen())


# ==============================================================================
# Main App
# ==============================================================================
class RunnerApp(App):
    CSS_PATH = "runner.tcss"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_session = None

    def on_mount(self) -> None:
        self.push_screen(WelcomeScreen())

    def create_new_session(self, lang) -> None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        session = {
            "id": session_id,
            "language": lang,
            "code": TEMPLATES.get(lang, ""),
            "output": "",
            "updated_at": datetime.now().isoformat()
        }
        save_session(session)
        self.current_session = session
        self.switch_screen(EditorScreen())
        
    def load_session(self, session_id) -> None:
        session = load_session_by_id(session_id)
        if session:
            self.current_session = session
            self.switch_screen(EditorScreen())


def main():
    app = RunnerApp()
    app.run()

if __name__ == "__main__":
    main()
