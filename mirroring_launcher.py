import os
import sys
import subprocess
import re
import threading
import queue
import json
import time
import ctypes
import urllib.request
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw

# ----------------------------------------------------
# Helper Functions for UI display & fallbacks
# ----------------------------------------------------
def get_default_icon_image():
    if os.path.exists(DEFAULT_ICON_PNG):
        try:
            return Image.open(DEFAULT_ICON_PNG)
        except Exception:
            pass
            
    # Draw fallback image if file not found
    img = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Modern rounded rectangle for premium app layout
    draw.rounded_rectangle([2, 2, 45, 45], radius=10, fill=(0, 122, 204, 255))
    # Tech lines design in the center
    draw.rectangle([16, 12, 32, 36], fill=(255, 255, 255, 255))
    draw.rectangle([12, 16, 36, 32], fill=(255, 255, 255, 255))
    draw.rounded_rectangle([18, 18, 30, 30], radius=3, fill=(0, 122, 204, 255))
    return img

def truncate_text(text, max_len=14):
    if len(text) > max_len:
        return text[:max_len-2] + ".."
    return text

def get_density_score(path):
    p = path.lower()
    if 'xxxhdpi' in p: return 6
    if 'xxhdpi' in p: return 5
    if 'xhdpi' in p: return 4
    if 'hdpi' in p: return 3
    if 'mdpi' in p: return 2
    if 'ldpi' in p: return 1
    return 0


# ----------------------------------------------------
# Common Android App Labels Map (Local Translation Dictionary)
# ----------------------------------------------------
COMMON_APP_NAMES = {}

SEARCH_TRANSLATIONS = {
    "카카오": "kakao",
    "텔레그램": "telegram",
    "유튜브": "youtube",
    "페이스북": "facebook",
    "인스타": "instagram",
    "네이버": "naver",
    "라인": "line",
    "구글": "google",
    "설정": "setting",
    "크롬": "chrome",
    "지도": "map",
    "카메라": "camera",
    "갤러리": "gallery",
    "계산기": "calculator",
    "캘린더": "calendar",
    "노트": "note",
    "파일": "file",
    "메시지": "message",
    "전화": "phone",
    "시계": "clock",
    "게임": "game",
    "배그": "pubg",
    "원신": "genshin",
    "스타레일": "starrail"
}


# Set AppUserModelID to ensure the taskbar group matches on Windows
try:
    myappid = 'DOHA1012.UniversalMirroring.Launcher.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# ----------------------------------------------------
# Paths configurations
# ----------------------------------------------------
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()
ADB_PATH = os.path.join(BASE_PATH, "bin", "adb", "adb.exe")
SCRCPY_PATH = os.path.join(BASE_PATH, "bin", "scrcpy", "scrcpy.exe")

# Fallback paths
if not os.path.exists(ADB_PATH):
    ADB_PATH = os.path.join(BASE_PATH, "bin", "adb.exe")
if not os.path.exists(SCRCPY_PATH):
    SCRCPY_PATH = os.path.join(BASE_PATH, "bin", "scrcpy.exe")

if not os.path.exists(ADB_PATH):
    ADB_PATH = os.path.join(BASE_PATH, "adb.exe")
if not os.path.exists(SCRCPY_PATH):
    SCRCPY_PATH = os.path.join(BASE_PATH, "scrcpy.exe")

# Check C:\scrcpy as secondary fallback
if not os.path.exists(ADB_PATH):
    ADB_PATH = r"C:\scrcpy\adb.exe"
if not os.path.exists(SCRCPY_PATH):
    SCRCPY_PATH = r"C:\scrcpy\scrcpy.exe"

# Set ADB environment so scrcpy can resolve it
os.environ["ADB"] = ADB_PATH

# Cache directory setups
CACHE_DIR = os.path.join(BASE_PATH, "cache")
ICON_CACHE_DIR = os.path.join(CACHE_DIR, "icons")
os.makedirs(ICON_CACHE_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(BASE_PATH, "config.json")
LABEL_CACHE_PATH = os.path.join(CACHE_DIR, "app_labels.json")
DEFAULT_ICON_PNG = os.path.join(BASE_PATH, "launcher_icon.png")
DEFAULT_ICON_ICO = os.path.join(BASE_PATH, "launcher_icon.ico")

# ----------------------------------------------------
# CMD execution helper (Runs silently)
# ----------------------------------------------------
def run_cmd(args):
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), -1

# ----------------------------------------------------
# Helper to identify real Wi-Fi private IP address ranges
# ----------------------------------------------------
def is_private_ip(ip):
    if not ip or ip.startswith("127."):
        return False
    if ip.startswith("169.254."):
        return False
    # Filter common mobile carrier IP subnets like 192.0.0.x or 10.x.x.x (if it's not a home router)
    # Home Wi-Fi usually uses 192.168.x.x, 172.16.x.x ~ 172.31.x.x, or 10.0.x.x/10.1.x.x subnets.
    parts = list(map(int, ip.split('.')))
    if len(parts) != 4:
        return False
    
    # Class C (Most common home Wi-Fi routers)
    if parts[0] == 192 and parts[1] == 168:
        return True
    # Class B (e.g. 172.30.x.x or 172.16.x.x)
    if parts[0] == 172:
        return True
    # Class A (Usually 10.0.0.0 to 10.255.255.255)
    # Allow Class A but exclude generic cellular if possible.
    # Typically home network Class A router subnets are small like 10.0.0.x or 10.1.1.x
    if parts[0] == 10:
        return True
        
    return False

# ----------------------------------------------------
# Main Launcher GUI
# ----------------------------------------------------
class MirroringLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("미러링 바로연결 (Universal Mirroring Launcher)")
        self.root.geometry("680x560")
        self.root.resizable(False, False)
        
        # Load launcher icon
        if os.path.exists(DEFAULT_ICON_ICO):
            try:
                self.root.iconbitmap(DEFAULT_ICON_ICO)
            except Exception:
                pass
        
        self.style = ttk.Style()
        self.style.theme_use("vista")
        
        self.devices = []
        self.all_apps = []        # Scanned apps: [{"package": "...", "label": "..."}]
        self.favorites = []       # Saved favorites: [{"package": "...", "label": "...", "nickname": "..."}]
        self.app_labels_cache = {}  # Cache for Play Store app labels
        self.load_app_labels_cache()
        self.selected_app = None  # Selected favorite app object
        
        self.is_scraping_running = False
        self.scraping_total = 0
        self.scraping_done = 0
        self.lbl_loading_status = None
        self.scan_tree_ref = None
        self.scan_win_ref = None
        
        # Main frames layout
        self.main_frame = ttk.Frame(self.root, padding="15")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title Label
        title_label = ttk.Label(
            self.main_frame,
            text="📱 미러링 바로연결 (Universal Launcher)",
            font=("Malgun Gothic", 16, "bold"),
            foreground="#007acc"
        )
        title_label.pack(pady=(0, 10))
        
        # --- Top: Device Selection & Wireless Connection ---
        top_frame = ttk.LabelFrame(self.main_frame, text=" 1. 기기 무선 연결 및 설정 ", padding="8")
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Dropdown row
        row1 = ttk.Frame(top_frame)
        row1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row1, text="기기 선택:").pack(side=tk.LEFT, padx=(0, 5))
        self.dev_var = tk.StringVar()
        self.cb_devices = ttk.Combobox(row1, textvariable=self.dev_var, state="readonly", width=30)
        self.cb_devices.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.cb_devices.bind("<<ComboboxSelected>>", self.on_device_selected)
        
        self.btn_refresh = ttk.Button(row1, text="기기새로고침", command=self.refresh_devices)
        self.btn_refresh.pack(side=tk.RIGHT)
        
        # IP Connect row
        row2 = ttk.Frame(top_frame)
        row2.pack(fill=tk.X)
        
        ttk.Label(row2, text="무선 IP 주소:").pack(side=tk.LEFT, padx=(0, 5))
        self.txt_ip = ttk.Entry(row2, width=15)
        self.txt_ip.insert(0, "192.168.0.16")
        self.txt_ip.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_connect = ttk.Button(row2, text="무선 연결", command=self.connect_wireless)
        self.btn_connect.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_auto = ttk.Button(row2, text="★ USB 기기로 무선 자동 설정", command=self.auto_wireless_setup)
        self.btn_auto.pack(side=tk.RIGHT)
        
        # --- Middle Layout: Left (Favorites Grid), Right (Settings) ---
        mid_frame = ttk.Frame(self.main_frame)
        mid_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Left: Favorites
        fav_lf = ttk.LabelFrame(mid_frame, text=" 2. 즐겨찾기 앱 목록 ", padding="8")
        fav_lf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Grid canvas & scrollbar for favorites
        self.canvas = tk.Canvas(fav_lf, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(fav_lf, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind mouse wheel to canvas and scrollable_frame
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right: Settings
        set_lf = ttk.LabelFrame(mid_frame, text=" 3. 미러링 화면 설정 ", padding="8", width=220)
        set_lf.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        set_lf.pack_propagate(False)
        
        # Resolution dropdown
        ttk.Label(set_lf, text="해상도 선택:").pack(anchor=tk.W, pady=(5, 2))
        self.res_var = tk.StringVar(value="1280x720")
        self.cb_res = ttk.Combobox(
            set_lf, 
            textvariable=self.res_var, 
            values=["3840x2160", "2560x1440", "1920x1080", "1600x900", "1280x720", "960x540"], 
            state="readonly"
        )
        self.cb_res.pack(fill=tk.X, pady=(0, 10))
        
        # Borderless fullscreen check
        self.borderless_var = tk.BooleanVar(value=False)
        self.chk_borderless = ttk.Checkbutton(
            set_lf, 
            text="테두리 없는 전체화면", 
            variable=self.borderless_var
        )
        self.chk_borderless.pack(anchor=tk.W, pady=(0, 10))
        
        # Mirroring modes: Virtual Display vs Direct Duplicate
        ttk.Label(set_lf, text="미러링 방식 선택:").pack(anchor=tk.W, pady=(5, 2))
        self.mode_var = tk.StringVar(value="virtual")
        ttk.Radiobutton(
            set_lf, 
            text="독립 가상 창 (권장)", 
            value="virtual", 
            variable=self.mode_var
        )        .pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            set_lf, 
            text="기기 화면 복제 (동일 화면)", 
            value="direct", 
            variable=self.mode_var
        )        .pack(anchor=tk.W, pady=2)
        
        # --- Bottom Layout: Actions ---
        btn_row = ttk.Frame(self.main_frame)
        btn_row.pack(fill=tk.X)
        
        self.btn_app_list = ttk.Button(btn_row, text="➕ 전체 앱 스캔 및 즐겨찾기 등록", command=self.open_app_list_window)
        self.btn_app_list.pack(side=tk.LEFT, ipady=5)
        
        self.btn_launch = tk.Button(
            btn_row, 
            text="선택한 앱 실행 및 미러링", 
            font=("Malgun Gothic", 11, "bold"),
            bg="#4caf50", 
            fg="white", 
            relief=tk.RAISED, 
            bd=1,
            command=self.launch_game
        )
        self.btn_launch.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(15, 0), ipady=5)
        
        # Status Bar
        self.lbl_status = ttk.Label(self.main_frame, text="준비됨", font=("Malgun Gothic", 8), foreground="gray")
        self.lbl_status.pack(anchor=tk.W, pady=(8, 0))
        
        # Initialize configuration and load devices
        self.load_config()
        self.refresh_devices()

    def set_status(self, text, color="gray"):
        self.lbl_status.config(text=text, foreground=color)
        self.root.update_idletasks()

    # ----------------------------------------------------
    # Device scanning and connection
    # ----------------------------------------------------
    def refresh_devices(self):
        self.set_status("기기 목록 불러오는 중...", "blue")
        def run():
            stdout, stderr, code = run_cmd([ADB_PATH, "devices"])
            devs = []
            lines = stdout.splitlines()
            for line in lines:
                if "List of devices attached" in line or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    devs.append(f"{parts[0]} ({parts[1]})")
            
            self.root.after(0, lambda: self.update_devices(devs))
        threading.Thread(target=run, daemon=True).start()

    def update_devices(self, devs):
        self.cb_devices['values'] = devs
        self.devices = devs
        if devs:
            # Try to restore last-used device
            last_ip = self.txt_ip.get().strip()
            matched = False
            for i, d in enumerate(devs):
                if last_ip in d:
                    self.cb_devices.current(i)
                    matched = True
                    break
            if not matched:
                self.cb_devices.current(0)
            self.set_status(f"기기 {len(devs)}대 감지됨", "green")
            self.on_device_selected(None)
        else:
            self.dev_var.set("")
            self.set_status("감지된 기기 없음", "red")
            self.all_apps = []

    def on_device_selected(self, event):
        # Trigger background loading of apps for this device
        selected = self.dev_var.get()
        if not selected:
            return
        dev_id = selected.split()[0]
        self.set_status(f"기기 ({dev_id}) 앱 인벤토리 로딩 중...", "blue")
        
        # Load apps async
        def run_load():
            # Get list of launcher activities (without problematic --query-as-user)
            cmd_args = [
                ADB_PATH, "-s", dev_id, "shell", 
                "cmd package query-activities -a android.intent.action.MAIN -c android.intent.category.LAUNCHER"
            ]
            stdout, stderr, code = run_cmd(cmd_args)
            pkgs = set()
            
            # Parse cmd output for package names
            for line in stdout.splitlines():
                m1 = re.search(r"packageName=([^\s]+)", line)
                if m1:
                    pkgs.add(m1.group(1).strip())
                else:
                    m2 = re.search(r"name=([^/]+)/", line)
                    if m2:
                        pkgs.add(m2.group(1).strip())
            
            # Fallback/Supplemental: Get user-installed third-party apps
            stdout_pm, _, _ = run_cmd([ADB_PATH, "-s", dev_id, "shell", "pm list packages -3"])
            for line in stdout_pm.splitlines():
                if line.startswith("package:"):
                    pkg = line.replace("package:", "").strip()
                    pkgs.add(pkg)
            
            # Build app lists with locally resolved labels
            apps = []
            for pkg in sorted(list(pkgs)):
                label = self.resolve_app_label_locally(pkg)
                apps.append({"package": pkg, "label": label})
                
            # Sort apps alphabetically by label
            apps.sort(key=lambda x: x["label"].lower())
            
            self.root.after(0, lambda: self.finish_apps_loading(apps))
        threading.Thread(target=run_load, daemon=True).start()

    def finish_apps_loading(self, apps):
        self.all_apps = apps
        self.set_status(f"기기 앱 목록 스캔 완료 ({len(apps)}개 앱)", "green")
        self.start_global_async_label_scraping()
        
        # Auto-extract missing or fallback icons for favorites
        selected = self.dev_var.get()
        if selected:
            dev_id = selected.split()[0]
            for fav in self.favorites:
                pkg = fav["package"]
                lbl = fav["label"]
                png_path = os.path.join(ICON_CACHE_DIR, f"{pkg}.png")
                if not os.path.exists(png_path) or (os.path.exists(png_path) and os.path.getsize(png_path) <= 500):
                    self.extract_app_icon(dev_id, pkg, lbl)

    def connect_wireless(self):
        ip = self.txt_ip.get().strip()
        if not ip:
            messagebox.showerror("오류", "IP 주소를 입력하세요.")
            return
        self.set_status(f"무선 연결 시도 중 ({ip}:5555)...", "blue")
        self.btn_connect.config(state=tk.DISABLED)
        
        def run():
            stdout, stderr, code = run_cmd([ADB_PATH, "connect", f"{ip}:5555"])
            success = "connected to" in stdout.lower()
            def done():
                self.btn_connect.config(state=tk.NORMAL)
                if success:
                    messagebox.showinfo("연결 성공", f"{ip}:5555 무선 연결 성공!")
                    self.set_status("무선 연결 성공", "green")
                else:
                    messagebox.showerror("연결 실패", f"무선 연결에 실패했습니다:\n{stdout}\n{stderr}")
                    self.set_status("무선 연결 실패", "red")
                self.refresh_devices()
            self.root.after(0, done)
        threading.Thread(target=run, daemon=True).start()

    def auto_wireless_setup(self):
        self.set_status("자동 무선 연결 구성 진행 중...", "blue")
        self.btn_auto.config(state=tk.DISABLED)
        
        def run():
            # Find USB device (exclude any device that is wireless, i.e., has IP format or port colon)
            stdout, _, _ = run_cmd([ADB_PATH, "devices"])
            usb_dev = None
            for line in stdout.splitlines():
                if "List of devices attached" in line or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    d_id = parts[0]
                    # Check if the device ID looks like an IP address or contains colon (wireless port)
                    is_wireless = ":" in d_id or re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", d_id)
                    if not is_wireless:
                        usb_dev = d_id
                        break
            
            if not usb_dev:
                def err():
                    self.btn_auto.config(state=tk.NORMAL)
                    messagebox.showerror("오류", "USB로 연결된 스마트폰을 감지할 수 없습니다. 케이블 연결을 확인해 주세요.")
                    self.set_status("USB 기기 없음", "red")
                self.root.after(0, err)
                return
            
            # Setup tcpip port
            run_cmd([ADB_PATH, "-s", usb_dev, "tcpip", "5555"])
            # Essential delay to allow Android to spin up the listener port
            time.sleep(1.5)
            
            # Fetch real Wi-Fi IP address (ignore mobile carrier networks)
            phone_ip = None
            
            # Strategy 1: check ip route
            ip_stdout, _, _ = run_cmd([ADB_PATH, "-s", usb_dev, "shell", "ip route"])
            for line in ip_stdout.splitlines():
                if "src" in line:
                    m = re.search(r"src\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
                    if m:
                        candidate = m.group(1)
                        if is_private_ip(candidate):
                            phone_ip = candidate
                            break
            
            # Strategy 2: check all IPv4 interfaces
            if not phone_ip:
                ip_stdout, _, _ = run_cmd([ADB_PATH, "-s", usb_dev, "shell", "ip -4 addr show"])
                candidates = re.findall(r"inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", ip_stdout)
                for candidate in candidates:
                    if is_private_ip(candidate):
                        phone_ip = candidate
                        break

            # Strategy 3: dumpsys wifi (useful on some restricted systems)
            if not phone_ip:
                wifi_stdout, _, _ = run_cmd([ADB_PATH, "-s", usb_dev, "shell", "dumpsys wifi"])
                candidates = re.findall(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", wifi_stdout)
                for candidate in candidates:
                    if is_private_ip(candidate):
                        phone_ip = candidate
                        break
            
            if not phone_ip:
                def ip_err():
                    self.btn_auto.config(state=tk.NORMAL)
                    messagebox.showerror("오류", "기기 Wi-Fi IP 주소를 파악할 수 없습니다. 폰이 와이파이에 올바르게 연결되어 있는지 확인해 주세요.")
                    self.set_status("IP 획득 실패", "red")
                self.root.after(0, ip_err)
                return
            
            # Disconnect existing sessions to clear dead routing locks
            run_cmd([ADB_PATH, "disconnect", f"{phone_ip}:5555"])
            time.sleep(0.5)
            
            # Connect wirelessly
            run_cmd([ADB_PATH, "connect", f"{phone_ip}:5555"])
            
            def success():
                self.btn_auto.config(state=tk.NORMAL)
                self.txt_ip.delete(0, tk.END)
                self.txt_ip.insert(0, phone_ip)
                messagebox.showinfo("설정 완료", f"자동 연결에 성공했습니다!\nIP 주소: {phone_ip}:5555\n\n이제 USB 케이블을 제거하셔도 됩니다.")
                self.set_status("자동 설정 완료", "green")
                self.refresh_devices()
            self.root.after(0, success)
            
        threading.Thread(target=run, daemon=True).start()

    # ----------------------------------------------------
    # Favorites layout and card rendering
    # ----------------------------------------------------
    def update_favorites_ui(self):
        # Clear current grid
        for child in self.scrollable_frame.winfo_children():
            child.destroy()
            
        if not self.favorites:
            lbl = ttk.Label(self.scrollable_frame, text="즐겨찾기에 등록된 앱이 없습니다.\n아래 [전체 앱 스캔 및 즐겨찾기 등록] 버튼을 눌러 등록하세요.", font=("Malgun Gothic", 9), justify=tk.CENTER)
            lbl.pack(pady=40, padx=20)
            return

        self.cards = {}
        for index, app in enumerate(self.favorites):
            pkg = app["package"]
            name = app.get("nickname", app["label"])
            
            # Resolve icon image path
            icon_path = os.path.join(ICON_CACHE_DIR, f"{pkg}.png")
            
            # Create Tkinter PhotoImage card with fallback helper
            try:
                if os.path.exists(icon_path):
                    pil_img = Image.open(icon_path).resize((48, 48), Image.Resampling.LANCZOS)
                else:
                    pil_img = get_default_icon_image()
                img = ImageTk.PhotoImage(pil_img)
            except Exception:
                try:
                    pil_img = get_default_icon_image()
                    img = ImageTk.PhotoImage(pil_img)
                except Exception:
                    img = None

            # Card outer frame
            card = ttk.Frame(self.scrollable_frame, style="Card.TFrame", padding=5, borderwidth=1, relief="solid")
            card.grid(row=index // 3, column=index % 3, padx=8, pady=8, sticky="nsew")
            
            # Prevent image from garbage collection
            card.image = img
            
            # Elements inside card
            lbl_icon = ttk.Label(card, image=img)
            lbl_icon.pack(pady=(5, 2))
            
            # Prevent layout breaking due to long names / packages
            display_name = truncate_text(name, max_len=13)
            display_pkg = truncate_text(pkg, max_len=16)
            
            lbl_name = ttk.Label(card, text=display_name, font=("Malgun Gothic", 9, "bold"), width=13, anchor="center", justify=tk.CENTER)
            lbl_name.pack(pady=(0, 2))
            
            lbl_pkg = ttk.Label(card, text=display_pkg, font=("Malgun Gothic", 7), foreground="gray", width=16, anchor="center")
            lbl_pkg.pack(pady=(0, 5))
            
            # Events
            card.bind("<Button-1>", lambda e, a=app: self.select_favorite(a))
            lbl_icon.bind("<Button-1>", lambda e, a=app: self.select_favorite(a))
            lbl_name.bind("<Button-1>", lambda e, a=app: self.select_favorite(a))
            lbl_pkg.bind("<Button-1>", lambda e, a=app: self.select_favorite(a))
            
            # Right-click context menu (Remove / Rename)
            card.bind("<Button-3>", lambda e, a=app: self.show_context_menu(e, a))
            lbl_icon.bind("<Button-3>", lambda e, a=app: self.show_context_menu(e, a))
            lbl_name.bind("<Button-3>", lambda e, a=app: self.show_context_menu(e, a))
            lbl_pkg.bind("<Button-3>", lambda e, a=app: self.show_context_menu(e, a))
            
            # Mouse wheel scroll propagation
            def _on_card_mousewheel(event):
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            card.bind("<MouseWheel>", _on_card_mousewheel)
            lbl_icon.bind("<MouseWheel>", _on_card_mousewheel)
            lbl_name.bind("<MouseWheel>", _on_card_mousewheel)
            lbl_pkg.bind("<MouseWheel>", _on_card_mousewheel)
            
            self.cards[pkg] = card
            
        self.highlight_selected_card()

    def select_favorite(self, app):
        self.selected_app = app
        self.highlight_selected_card()
        self.set_status(f"선택됨: {app.get('nickname', app['label'])} ({app['package']})", "blue")

    def highlight_selected_card(self):
        for pkg, card in self.cards.items():
            if self.selected_app and self.selected_app["package"] == pkg:
                card.config(relief="ridge", borderwidth=2)
            else:
                card.config(relief="solid", borderwidth=1)

    def show_context_menu(self, event, app):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="이름 변경 (별칭 지정)", command=lambda: self.rename_favorite(app))
        menu.add_separator()
        menu.add_command(label="즐겨찾기 삭제", command=lambda: self.remove_from_favorites(app))
        menu.post(event.x_root, event.y_root)

    def rename_favorite(self, app):
        old_name = app.get("nickname", app["label"])
        new_name = simpledialog.askstring("이름 변경", f"'{old_name}'의 별칭을 입력하세요:", initialvalue=old_name)
        if new_name is not None:
            app["nickname"] = new_name.strip()
            self.save_config()
            self.update_favorites_ui()
            if self.selected_app and self.selected_app["package"] == app["package"]:
                self.selected_app = app
                self.highlight_selected_card()

    def remove_from_favorites(self, app):
        self.favorites = [x for x in self.favorites if x["package"] != app["package"]]
        # Clean local icons if not default
        icon_png = os.path.join(ICON_CACHE_DIR, f"{app['package']}.png")
        icon_ico = os.path.join(ICON_CACHE_DIR, f"{app['package']}.ico")
        if os.path.exists(icon_png):
            try: os.remove(icon_png)
            except: pass
        if os.path.exists(icon_ico):
            try: os.remove(icon_ico)
            except: pass
            
        if self.selected_app and self.selected_app["package"] == app["package"]:
            self.selected_app = None
            
        self.save_config()
        self.update_favorites_ui()

    # ----------------------------------------------------
    # Scan and Add Favorite Dialog Window
    # ----------------------------------------------------
    def open_app_list_window(self):
        selected_dev = self.dev_var.get()
        if not selected_dev:
            messagebox.showerror("오류", "먼저 상단에서 연결된 기기를 선택해 주세요.")
            return
            
        if not self.all_apps:
            messagebox.showinfo("대기", "앱 목록을 수집 중입니다. 잠시 후 다시 시도해 주세요.")
            return
            
        # Spawn Top Level Window
        list_win = tk.Toplevel(self.root)
        list_win.title("설치된 전체 앱 검색 및 추가")
        list_win.geometry("500x520")
        list_win.resizable(False, False)
        list_win.grab_set()
        
        self.scan_win_ref = list_win
        
        # Loading Status Label at the very top
        self.lbl_loading_status = ttk.Label(list_win, text="", font=("Malgun Gothic", 9, "bold"))
        self.lbl_loading_status.pack(fill=tk.X, padx=10, pady=(10, 0))
        self.update_loading_status_ui()
        
        # Search Entry Row
        search_row = ttk.Frame(list_win, padding="10")
        search_row.pack(fill=tk.X)
        
        ttk.Label(search_row, text="검색어:").pack(side=tk.LEFT, padx=(0, 5))
        search_var = tk.StringVar()
        entry_search = ttk.Entry(search_row, textvariable=search_var)
        entry_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        entry_search.focus()
        
        btn_search = ttk.Button(search_row, text="검색", command=lambda: do_search())
        btn_search.pack(side=tk.LEFT, padx=(5, 0))
        
        # Treeview to display list
        tree_frame = ttk.Frame(list_win, padding="10")
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        cols = ("Name", "Package")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)
        tree.heading("Name", text="앱 이름")
        tree.heading("Package", text="패키지명 (ID)")
        tree.column("Name", width=180)
        tree.column("Package", width=280)
        
        self.scan_tree_ref = tree
        
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate List
        def populate(filter_str=""):
            # Clear tree
            for item in tree.get_children():
                tree.delete(item)
            
            clean_filter = filter_str.replace(" ", "").lower()
            
            # Translate korean search query to English equivalent if any
            english_filter = ""
            for kr_key, en_val in SEARCH_TRANSLATIONS.items():
                if kr_key in clean_filter:
                    english_filter = en_val
                    break
            
            # Add matching
            for app in self.all_apps:
                pkg = app["package"]
                # Resolve current label dynamically (helps pick up scraped labels)
                lbl = self.resolve_app_label_locally(pkg)
                app["label"] = lbl  # Keep local all_apps record updated
                
                clean_lbl = lbl.replace(" ", "").lower()
                clean_pkg = pkg.replace(" ", "").lower()
                
                is_match = (
                    not clean_filter or
                    clean_filter in clean_lbl or
                    clean_filter in clean_pkg or
                    (english_filter and english_filter in clean_lbl) or
                    (english_filter and english_filter in clean_pkg)
                )
                
                if is_match:
                    # Check if already added
                    suffix = ""
                    if any(x["package"] == pkg for x in self.favorites):
                        suffix = " (등록됨)"
                    tree.insert("", tk.END, values=(lbl + suffix, pkg))
                    
        def do_search():
            filter_str = search_var.get().strip()
            populate(filter_str)
            
            shown_packages = []
            for item in tree.get_children():
                values = tree.item(item, "values")
                if values:
                    shown_packages.append(values[1])
                    
            to_scrape = []
            for app in self.all_apps:
                pkg = app["package"]
                if pkg in shown_packages and pkg not in self.app_labels_cache:
                    to_scrape.append(app)
                    
            if to_scrape and len(shown_packages) <= 20:
                self.start_async_label_scraping_pinpoint(tree, list_win, to_scrape)
                    
        populate()
        entry_search.bind("<Return>", lambda e: do_search())
        
        # Add logic
        def on_add():
            sel = tree.selection()
            if not sel:
                return
            item = tree.item(sel[0])
            lbl, pkg = item["values"]
            
            # Clean registration suffix
            lbl = lbl.replace(" (등록됨)", "")
            
            if any(x["package"] == pkg for x in self.favorites):
                messagebox.showwarning("주의", "이미 즐겨찾기에 등록된 앱입니다.")
                return
                
            # Ask nickname
            nick = simpledialog.askstring("즐겨찾기 추가", f"'{lbl}'의 런처 표시 이름을 지정하세요:", initialvalue=lbl, parent=list_win)
            if nick is None:
                return # Canceled
                
            nick = nick.strip() if nick.strip() else lbl
            
            # Add element placeholder
            app_data = {"package": pkg, "label": lbl, "nickname": nick}
            self.favorites.append(app_data)
            self.save_config()
            self.update_favorites_ui()
            
            # Trigger asynchronous icon extraction from phone
            self.set_status(f"'{lbl}' 아이콘 추출 진행 중...", "blue")
            list_win.destroy()
            
            self.extract_app_icon(selected_dev.split()[0], pkg, lbl)
 
        btn_row = ttk.Frame(list_win, padding="10")
        btn_row.pack(fill=tk.X)
        
        ttk.Button(btn_row, text="즐겨찾기 추가", command=on_add).pack(fill=tk.X)
        tree.bind("<Double-1>", lambda e: on_add())
        
        def on_close():
            self.lbl_loading_status = None
            self.scan_tree_ref = None
            self.scan_win_ref = None
            list_win.destroy()
            
        list_win.protocol("WM_DELETE_WINDOW", on_close)

    def start_async_label_scraping_pinpoint(self, tree, list_win, to_scrape):
        def scrape_worker():
            updated_any = False
            for app in to_scrape:
                if not list_win.winfo_exists():
                    break
                pkg = app["package"]
                scraped_label = self.scrape_play_store_label(pkg)
                if scraped_label:
                    self.app_labels_cache[pkg] = scraped_label
                    app["label"] = scraped_label
                    updated_any = True
                    
                    def update_ui(p=pkg, l=scraped_label):
                        try:
                            if self.scan_win_ref and self.scan_win_ref.winfo_exists() and self.scan_tree_ref:
                                for item in self.scan_tree_ref.get_children():
                                    values = self.scan_tree_ref.item(item, "values")
                                    if values and values[1] == p:
                                        suffix = " (등록됨)" if any(x["package"] == p for x in self.favorites) else ""
                                        self.scan_tree_ref.set(item, "Name", l + suffix)
                                        break
                        except Exception:
                            pass
                    self.root.after(0, update_ui)
                time.sleep(0.3) # Pinpoint has high priority
                
            if updated_any:
                self.save_app_labels_cache()
                
        threading.Thread(target=scrape_worker, daemon=True).start()

    def start_global_async_label_scraping(self):
        to_scrape = []
        for app in self.all_apps:
            pkg = app["package"]
            if pkg not in self.app_labels_cache:
                to_scrape.append(app)
                
        if not to_scrape:
            self.is_scraping_running = False
            self.update_loading_status_ui()
            return
            
        self.is_scraping_running = True
        self.scraping_total = len(to_scrape)
        self.scraping_done = 0
        self.update_loading_status_ui()
        
        q = queue.Queue()
        for app in to_scrape:
            q.put(app)
            
        lock = threading.Lock()
        
        def worker():
            updated_any = False
            while not q.empty():
                try:
                    app = q.get_nowait()
                except queue.Empty:
                    break
                    
                pkg = app["package"]
                scraped_label = self.scrape_play_store_label(pkg)
                
                with lock:
                    self.scraping_done += 1
                    if scraped_label:
                        self.app_labels_cache[pkg] = scraped_label
                        app["label"] = scraped_label
                        updated_any = True
                        
                        def update_ui(p=pkg, l=scraped_label):
                            try:
                                if self.scan_win_ref and self.scan_win_ref.winfo_exists() and self.scan_tree_ref:
                                    for item in self.scan_tree_ref.get_children():
                                        values = self.scan_tree_ref.item(item, "values")
                                        if values and values[1] == p:
                                            suffix = " (등록됨)" if any(x["package"] == p for x in self.favorites) else ""
                                            self.scan_tree_ref.set(item, "Name", l + suffix)
                                            break
                            except Exception:
                                pass
                        self.root.after(0, update_ui)
                        
                    self.root.after(0, self.update_loading_status_ui)
                    
                time.sleep(0.1)
                q.task_done()
                
            if updated_any:
                with lock:
                    self.save_app_labels_cache()
                    
            with lock:
                if self.scraping_done >= self.scraping_total:
                    self.is_scraping_running = False
                    self.root.after(0, self.update_loading_status_ui)
                    
        for _ in range(5):
            threading.Thread(target=worker, daemon=True).start()

    def update_loading_status_ui(self):
        if self.lbl_loading_status and self.scan_win_ref and self.scan_win_ref.winfo_exists():
            if self.is_scraping_running:
                pct = int((self.scraping_done / self.scraping_total) * 100) if self.scraping_total > 0 else 0
                self.lbl_loading_status.config(
                    text=f"⏳ 앱 한글 이름 수집 중... (로딩 중 {pct}%) - 잠시 기다려 주세요.",
                    foreground="red"
                )
            else:
                self.lbl_loading_status.config(
                    text="✅ 모든 앱의 한글 이름 수집 및 스캔이 완료되었습니다.",
                    foreground="green"
                )

    # ----------------------------------------------------
    # High-speed asynchronous app icon extraction (unzip logic)
    # ----------------------------------------------------
    def extract_app_icon(self, dev_id, pkg, label):
        def run():
            local_png = os.path.join(ICON_CACHE_DIR, f"{pkg}.png")
            local_ico = os.path.join(ICON_CACHE_DIR, f"{pkg}.ico")
            debug_log_path = os.path.join(CACHE_DIR, "icon_debug.log")
            
            def log_write(msg):
                try:
                    with open(debug_log_path, "a", encoding="utf-8") as lf:
                        lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{pkg}] {msg}\n")
                except:
                    pass
            
            log_write("Starting extraction process...")
            log_write(f"Paths: local_png={local_png}, local_ico={local_ico}")
            
            # Step 0: Try Google Play Store first (best quality, extremely fast, bypasses bad local icon layers)
            log_write("Attempting Play Store high-res icon download...")
            success = self.download_play_store_icon(pkg, local_png)
            
            apk_path = None
            if success:
                log_write("Play Store icon download succeeded!")
            else:
                log_write("Play Store download failed. Falling back to local APK extraction...")
                log_write(f"ADB_PATH exists: {os.path.exists(ADB_PATH)} ({ADB_PATH})")
                
                # 1. Fetch APK Path on the phone
                stdout, stderr, code = run_cmd([ADB_PATH, "-s", dev_id, "shell", f"pm path {pkg}"])
                log_write(f"pm path code={code}, stdout={stdout.strip()}, stderr={stderr.strip()}")
                
                for line in stdout.splitlines():
                    if line.startswith("package:"):
                        apk_path = line.replace("package:", "").strip()
                        break
                
                log_write(f"Resolved APK path on phone: {apk_path}")
            
            if apk_path and not success:
                # 2. Pull remote APK to local temp cache on PC
                temp_apk_pc = os.path.join(tempfile.gettempdir(), f"{pkg}_temp.apk")
                log_write(f"Pulling APK to: {temp_apk_pc}")
                pull_stdout, pull_stderr, code = run_cmd([ADB_PATH, "-s", dev_id, "pull", apk_path, temp_apk_pc])
                log_write(f"Pull code={code}, stdout={pull_stdout.strip()}, stderr={pull_stderr.strip()}")
                log_write(f"Temp APK exists on PC: {os.path.exists(temp_apk_pc)}")
                
                if code == 0 and os.path.exists(temp_apk_pc):
                    # 3. Use python's built-in zipfile to search for the icon inside the APK
                    try:
                        import zipfile
                        import io
                        log_write("Opening zipfile...")
                        with zipfile.ZipFile(temp_apk_pc, 'r') as zf:
                            namelist = zf.namelist()
                            png_files = [f for f in namelist if f.lower().endswith('.png')]
                            log_write(f"Total PNG files in zip: {len(png_files)}")
                            
                            icon_file = None
                            
                            # 3.1. Try local aapt.exe dump badging first (100% reliable for R8 and Unity engines)
                            AAPT_EXE = os.path.join(BASE_PATH, "bin", "aapt.exe")
                            if not os.path.exists(AAPT_EXE):
                                AAPT_EXE = os.path.join(BASE_PATH, "aapt.exe")
                                
                            if os.path.exists(AAPT_EXE):
                                log_write("Local aapt.exe detected. Running dump badging on PC...")
                                dump_stdout, dump_stderr, dump_code = run_cmd([AAPT_EXE, "dump", "badging", temp_apk_pc])
                                log_write(f"aapt dump code: {dump_code}")
                                
                                icon_paths = []
                                for line in dump_stdout.splitlines():
                                    if "application-icon" in line:
                                        m = re.search(r"application-icon-\d+:\'([^\']+)\'", line)
                                        if m:
                                            icon_paths.append(m.group(1))
                                        else:
                                            m2 = re.search(r"application-icon:\'([^\']+)\'", line)
                                            if m2:
                                                icon_paths.append(m2.group(1))
                                                
                                log_write(f"aapt parsed icon candidates: {icon_paths}")
                                if icon_paths:
                                    # Resolve the exact base name (handles adaptive icon XML structures)
                                    target_path = icon_paths[-1]
                                    base_name = os.path.basename(target_path).split('.')[0]
                                    log_write(f"aapt resolved icon base name: {base_name}")
                                    
                                    # Look for a PNG with the exact same base name in zip to avoid XML issues
                                    matched_pngs = [f for f in png_files if os.path.basename(f).lower() == f"{base_name.lower()}.png"]
                                    log_write(f"PNG files matching base name '{base_name}': {len(matched_pngs)}")
                                    if matched_pngs:
                                        # Sort by resolution/density
                                        matched_pngs.sort(key=lambda x: get_density_score(x), reverse=True)
                                        best_match = matched_pngs[0]
                                        best_size = len(zf.read(best_match))
                                        log_write(f"aapt best match: {best_match} ({best_size}B)")
                                        
                                        # Quality check: if the best match is tiny (<2KB), it's likely
                                        # a Unity/engine placeholder. Try adaptive foreground instead.
                                        if best_size < 2048:
                                            log_write(f"Best match too small ({best_size}B), checking adaptive foreground...")
                                            fg_candidates = [f for f in png_files if 'foreground' in f.lower() 
                                                           and ('ic_launcher' in f.lower() or base_name.lower() in f.lower())]
                                            if fg_candidates:
                                                fg_candidates.sort(key=lambda x: get_density_score(x), reverse=True)
                                                icon_file = fg_candidates[0]
                                                log_write(f"Using adaptive foreground: {icon_file}")
                                            else:
                                                icon_file = best_match
                                                log_write(f"No foreground found, using small match: {icon_file}")
                                        else:
                                            icon_file = best_match
                                            log_write(f"aapt selected resolved PNG path: {icon_file}")
                                    else:
                                        # No PNG with base name found. Check for adaptive foreground layer.
                                        fg_candidates = [f for f in png_files if 'foreground' in f.lower()
                                                       and ('ic_launcher' in f.lower() or base_name.lower() in f.lower())]
                                        if fg_candidates:
                                            fg_candidates.sort(key=lambda x: get_density_score(x), reverse=True)
                                            icon_file = fg_candidates[0]
                                            log_write(f"Using adaptive foreground (no base PNG): {icon_file}")
                                        elif target_path.lower().endswith('.png'):
                                            icon_file = target_path
                                            log_write(f"aapt fell back to direct path: {icon_file}")
                                    

                                
                            # Heuristics step 1: Search standard launcher icons (exclude adaptive background/foreground layers)
                            if not icon_file:
                                launcher_candidates = [f for f in png_files if 'ic_launcher' in f.lower() and 'background' not in f.lower() and 'foreground' not in f.lower()]
                                log_write(f"Step 1 (ic_launcher) candidates count: {len(launcher_candidates)}")
                                if launcher_candidates:
                                    launcher_candidates.sort(key=lambda x: get_density_score(x), reverse=True)
                                    icon_file = launcher_candidates[0]
                                    log_write(f"Selected via Step 1: {icon_file}")
                                
                            # Heuristics step 2: Search other common app icon keywords (exclude adaptive layers)
                            if not icon_file:
                                other_keywords = ['app_icon', 'appicon', 'game_icon', 'gameicon', 'logo', 'ic_app', 'launcher_icon']
                                candidates = []
                                for kw in other_keywords:
                                    candidates.extend([f for f in png_files if kw in f.lower() and 'background' not in f.lower() and 'foreground' not in f.lower()])
                                log_write(f"Step 2 (keywords) candidates count: {len(candidates)}")
                                if candidates:
                                    candidates.sort(key=lambda x: get_density_score(x), reverse=True)
                                    icon_file = candidates[0]
                                    log_write(f"Selected via Step 2: {icon_file}")
                                    
                            # Heuristics step 3: Search for drawable/mipmap having 'icon' or 'launcher'
                            if not icon_file:
                                fallback_candidates = [f for f in png_files if ('res/mipmap' in f or 'res/drawable' in f or 'r/mipmap' in f or 'r/drawable' in f) and ('icon' in f.lower() or 'launcher' in f.lower())]
                                log_write(f"Step 3 (mipmap/drawable + icon/launcher) count: {len(fallback_candidates)}")
                                if fallback_candidates:
                                    fallback_candidates.sort(key=lambda x: get_density_score(x), reverse=True)
                                    icon_file = fallback_candidates[0]
                                    log_write(f"Selected via Step 3: {icon_file}")
                                    
                            # Heuristics step 4: Any first image in standard mipmap/drawable folder
                            if not icon_file:
                                last_resort = [f for f in png_files if 'res/mipmap' in f or 'res/drawable' in f or 'r/mipmap' in f or 'r/drawable' in f]
                                log_write(f"Step 4 (any mipmap/drawable image) count: {len(last_resort)}")
                                if last_resort:
                                    icon_file = last_resort[0]
                                    log_write(f"Selected via Step 4: {icon_file}")
                                    
                            # Heuristics step 5: Fallback for obfuscated/optimized app icons
                            if not icon_file:
                                log_write("Step 5 (obfuscated app fallback): Analyzing square PNGs...")
                                res_png_files = [f for f in png_files if f.lower().startswith('res/') or f.lower().startswith('r/')]
                                square_candidates = []
                                for f in res_png_files:
                                    try:
                                        data = zf.read(f)
                                        img = Image.open(io.BytesIO(data))
                                        w, h = img.size
                                        if h > 0:
                                            ratio = w / h
                                            if abs(ratio - 1.0) < 0.02:
                                                square_candidates.append((f, w, len(data)))
                                    except Exception as ex:
                                        pass
                                log_write(f"Step 5 square candidates count: {len(square_candidates)}")
                                if square_candidates:
                                    square_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
                                    icon_file = square_candidates[0][0]
                                    log_write(f"Selected via Step 5: {icon_file} ({square_candidates[0][1]}x{square_candidates[0][1]})")
                                    
                            if icon_file:
                                icon_data = zf.read(icon_file)
                                with open(local_png, "wb") as icon_out:
                                    icon_out.write(icon_data)
                                success = True
                                log_write(f"Successfully extracted {icon_file} to local cache.")
                            else:
                                log_write("No icon file resolved from zip heuristics.")
                    except Exception as e:
                        log_write(f"Failed to parse APK zipfile: {str(e)}")
                    finally:
                        try:
                            os.remove(temp_apk_pc)
                            log_write("Cleaned up temp APK file.")
                        except Exception as ex:
                            log_write(f"Failed to clean up temp APK: {str(ex)}")
                else:
                    log_write("Skipped zip processing (pull failed or file missing).")

            # 4. Convert to ICO if extraction succeeded
            if success:
                try:
                    img = Image.open(local_png)
                    w, h = img.size
                    log_write(f"Extracted icon size: {w}x{h}")
                    
                    # If icon is too small, try Play Store high-res download
                    if w < 128 or h < 128:
                        log_write(f"Icon too small ({w}x{h}), attempting Play Store download...")
                        play_ok = self.download_play_store_icon(pkg, local_png)
                        if play_ok:
                            img = Image.open(local_png)
                            log_write(f"Play Store icon downloaded: {img.size[0]}x{img.size[1]}")
                    
                    img.save(local_ico, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
                    log_write("Successfully converted to ICO.")
                except Exception as e:
                    log_write(f"ICO Conversion failed: {str(e)}")
                    # Generate default icons from memory since extraction result was invalid
                    try:
                        log_write("Writing fallback blue icon from memory due to ICO conversion failure.")
                        default_img = get_default_icon_image()
                        default_img.save(local_png, format="PNG")
                        default_img.save(local_ico, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
                        log_write("Successfully wrote fallback icons.")
                    except Exception as ex:
                        log_write(f"Failed to generate default icons: {str(ex)}")
            else:
                # If APK extraction failed, try Play Store download first
                log_write("APK extraction failed. Trying Play Store icon download...")
                play_ok = self.download_play_store_icon(pkg, local_png)
                if play_ok:
                    try:
                        img = Image.open(local_png)
                        img.save(local_ico, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
                        log_write(f"Play Store icon saved: {img.size[0]}x{img.size[1]}")
                    except Exception as ex:
                        log_write(f"Play Store icon ICO conversion failed: {str(ex)}")
                else:
                    try:
                        log_write("All methods failed. Writing fallback blue icon from memory.")
                        default_img = get_default_icon_image()
                        default_img.save(local_png, format="PNG")
                        default_img.save(local_ico, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
                        log_write("Successfully wrote fallback icons.")
                    except Exception as ex:
                        log_write(f"Failed to generate default icons: {str(ex)}")
            
            # Try to scrape app label if not cached
            scraped_lbl = label
            if pkg not in self.app_labels_cache:
                scraped_title = self.scrape_play_store_label(pkg)
                if scraped_title:
                    self.app_labels_cache[pkg] = scraped_title
                    self.save_app_labels_cache()
                    scraped_lbl = scraped_title
                    
                    # Update active favorites array
                    updated_fav = False
                    for fav in self.favorites:
                        if fav["package"] == pkg:
                            fav["label"] = scraped_title
                            if fav.get("nickname") == label:
                                fav["nickname"] = scraped_title
                            updated_fav = True
                            break
                    if updated_fav:
                        self.save_config()
            
            # Reload GUI
            self.root.after(0, lambda: self.finish_icon_extraction(scraped_lbl))
            
        threading.Thread(target=run, daemon=True).start()

    def finish_icon_extraction(self, label):
        self.set_status(f"'{label}' 등록 완료 및 아이콘 로드 완료", "green")
        self.update_favorites_ui()

    # ----------------------------------------------------
    # Configuration Load / Save
    # ----------------------------------------------------
    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    ip = config.get("wireless_ip", "192.168.0.16")
                    res = config.get("resolution", "1280x720")
                    borderless = config.get("borderless", False)
                    mode = config.get("mirroring_mode", "virtual")
                    
                    self.txt_ip.delete(0, tk.END)
                    self.txt_ip.insert(0, ip)
                    self.res_var.set(res)
                    self.borderless_var.set(borderless)
                    self.mode_var.set(mode)
                    
                    self.favorites = config.get("favorites", [])
                    self.update_favorites_ui()
                    
                    # Restore selected app
                    sel_pkg = config.get("selected_favorite", "")
                    if sel_pkg:
                        for app in self.favorites:
                            if app["package"] == sel_pkg:
                                self.select_favorite(app)
                                break
            except Exception as e:
                print("Failed loading configuration profiles:", e)

    def save_config(self):
        config = {
            "wireless_ip": self.txt_ip.get().strip(),
            "resolution": self.res_var.get(),
            "borderless": self.borderless_var.get(),
            "mirroring_mode": self.mode_var.get(),
            "favorites": self.favorites,
            "selected_favorite": self.selected_app["package"] if self.selected_app else ""
        }
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print("Failed saving configuration profiles:", e)

    # ----------------------------------------------------
    # App Label Resolution & Caching helpers
    # ----------------------------------------------------
    def load_app_labels_cache(self):
        if os.path.exists(LABEL_CACHE_PATH):
            try:
                with open(LABEL_CACHE_PATH, "r", encoding="utf-8") as f:
                    self.app_labels_cache = json.load(f)
            except Exception as e:
                print("Failed loading app labels cache:", e)
                self.app_labels_cache = {}
        else:
            self.app_labels_cache = {}

    def save_app_labels_cache(self):
        try:
            with open(LABEL_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.app_labels_cache, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print("Failed saving app labels cache:", e)

    def clean_package_name_to_label(self, pkg):
        parts = pkg.split('.')
        # Skip common prefixes/suffixes
        meaningful_parts = [p for p in parts if p not in ('com', 'org', 'net', 'co', 'android', 'io', 'apps', 'app', 'google', 'samsung')]
        if not meaningful_parts:
            meaningful_parts = parts
        
        words = []
        for part in meaningful_parts:
            # Match camelCase or under_scores
            subparts = re.findall(r'[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)', part)
            if not subparts:
                subparts = [part]
            words.extend([sp.capitalize() for sp in subparts])
            
        return " ".join(words)

    def resolve_app_label_locally(self, pkg):
        if pkg in COMMON_APP_NAMES:
            return COMMON_APP_NAMES[pkg]
        if pkg in self.app_labels_cache:
            return self.app_labels_cache[pkg]
        return self.clean_package_name_to_label(pkg)

    def scrape_play_store_label(self, pkg):
        url = f"https://play.google.com/store/apps/details?id={pkg}&hl=ko"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate'
        })
        try:
            with urllib.request.urlopen(req, timeout=2.5) as response:
                content_encoding = response.info().get('Content-Encoding')
                raw_data = response.read()
                
                if content_encoding == 'gzip':
                    import gzip
                    html = gzip.decompress(raw_data).decode('utf-8', errors='ignore')
                else:
                    html = raw_data.decode('utf-8', errors='ignore')
                    
                m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                if m:
                    title = m.group(1)
                    # Normalize special dashes before processing
                    clean_title = title.replace("–", "-").replace("—", "-")
                    clean_title = clean_title.replace(" - Google Play 앱", "").replace(" - Apps on Google Play", "").strip()
                    if " - " in clean_title:
                        clean_title = clean_title.split(" - ")[0]
                    return clean_title.strip()
        except Exception:
            pass
        return None

    def download_play_store_icon(self, pkg, local_png_path):
        """Download high-res app icon from Google Play Store og:image tag."""
        url = f"https://play.google.com/store/apps/details?id={pkg}&hl=ko"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'Accept-Encoding': 'gzip, deflate'
        })
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                content_encoding = response.info().get('Content-Encoding')
                raw_data = response.read()
                if content_encoding == 'gzip':
                    import gzip
                    html = gzip.decompress(raw_data).decode('utf-8', errors='ignore')
                else:
                    html = raw_data.decode('utf-8', errors='ignore')
                
                m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                if m:
                    icon_url = m.group(1)
                    # Request 512x512 PNG from Google's image CDN
                    if '=' not in icon_url.split('/')[-1]:
                        icon_url += '=s512'
                    else:
                        icon_url = icon_url.split('=')[0] + '=s512'
                    
                    icon_req = urllib.request.Request(icon_url, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    with urllib.request.urlopen(icon_req, timeout=5) as icon_resp:
                        icon_data = icon_resp.read()
                        if len(icon_data) > 1000:
                            with open(local_png_path, 'wb') as f:
                                f.write(icon_data)
                            return True
        except Exception:
            pass
        return False

    # ----------------------------------------------------
    # Game launching & Dynamic Win32 Icon Skinning
    # ----------------------------------------------------
    def launch_game(self):
        selected_dev = self.dev_var.get()
        if not selected_dev:
            messagebox.showerror("오류", "연결된 기기가 없습니다.")
            return
            
        if not self.selected_app:
            messagebox.showerror("오류", "즐겨찾기에서 실행할 앱 카드를 마우스로 클릭하여 선택해 주세요.")
            return
            
        # Save profiles
        self.save_config()
        
        dev_id = selected_dev.split()[0]
        pkg = self.selected_app["package"]
        res = self.res_var.get()
        mode = self.mode_var.get()
        borderless = self.borderless_var.get()
        
        # Display Window Title based on App Name
        window_title = self.selected_app.get("nickname", self.selected_app["label"])
        
        self.set_status(f"'{window_title}' 무선 실행 및 스킨 변경 백그라운드 구동 중...", "blue")
        
        # Hide launcher immediately
        self.root.withdraw()
        
        def run():
            # Wake up display and dismiss lock guard
            run_cmd([ADB_PATH, "-s", dev_id, "shell", "input", "keyevent", "KEYCODE_WAKEUP"])
            run_cmd([ADB_PATH, "-s", dev_id, "shell", "wm", "dismiss-keyguard"])
            
            # Start target app using launcher monkey
            run_cmd([
                ADB_PATH, "-s", dev_id, "shell", "monkey",
                "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"
            ])
            
            # Configure scrcpy launch args
            scrcpy_args = [
                SCRCPY_PATH,
                "-s", dev_id,
                f"--start-app={pkg}",
                "--turn-screen-off",
                "--stay-awake",
                f"--window-title={window_title}"
            ]
            
            # Append specific mode parameters
            if mode == "virtual":
                scrcpy_args.append(f"--new-display={res}")
                scrcpy_args.append("--no-vd-system-decorations")
            else:
                # Direct mirroring uses max-size
                width = res.split('x')[0]
                scrcpy_args.append(f"--max-size={width}")
                
            if borderless:
                scrcpy_args.extend(["--window-borderless", "--fullscreen"])
                
            try:
                subprocess.Popen(
                    scrcpy_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception as e:
                def err(msg):
                    self.root.deiconify()
                    messagebox.showerror("실행 실패", f"scrcpy 실행에 실패했습니다:\n{msg}")
                self.root.after(0, lambda: err(str(e)))
                return
                
            # Background thread to skin the window icon dynamically
            icon_ico = os.path.join(ICON_CACHE_DIR, f"{pkg}.ico")
            if not os.path.exists(icon_ico):
                icon_ico = DEFAULT_ICON_ICO
                
            if os.path.exists(icon_ico):
                try:
                    user32 = ctypes.windll.user32
                    WM_SETICON = 0x80
                    ICON_SMALL = 0
                    ICON_BIG = 1
                    IMAGE_ICON = 1
                    LR_LOADFROMFILE = 0x0010
                    
                    # Wait up to 15 seconds for the window to appear
                    hwnd = None
                    for _ in range(75):
                        time.sleep(0.2)
                        hwnd = user32.FindWindowW(None, window_title)
                        if hwnd:
                            break
                            
                    if hwnd:
                        h_icon = user32.LoadImageW(
                            None,
                            icon_ico,
                            IMAGE_ICON,
                            0, 0,
                            LR_LOADFROMFILE
                        )
                        if h_icon:
                            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon)
                            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon)
                except Exception as ex:
                    print("Dynamic icon skinning exception:", ex)
                    
            # Safe exit
            import os as local_os
            local_os._exit(0)
            
        threading.Thread(target=run, daemon=True).start()

# ----------------------------------------------------
# Program Entry
# ----------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    
    # Custom Card layout styling
    style = ttk.Style()
    style.configure("Card.TFrame", background="#ffffff")
    
    app = MirroringLauncher(root)
    root.mainloop()
