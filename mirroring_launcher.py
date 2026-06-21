import os
import sys
import subprocess
import re
import threading
import json
import time
import ctypes
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk

# ----------------------------------------------------
# Common Android App Labels Map (Local Translation Dictionary)
# ----------------------------------------------------
COMMON_APP_NAMES = {
    "com.kakao.talk": "카카오톡",
    "com.nhn.android.nmap": "네이버 지도",
    "com.naver.labs.translator": "파파고",
    "com.naver.android.naverapp": "네이버",
    "com.naver.android.music": "VIBE (바이브)",
    "com.samsung.android.spay": "삼성 페이",
    "com.google.android.youtube": "유튜브",
    "com.google.android.apps.maps": "구글 지도",
    "com.instagram.android": "인스타그램",
    "com.facebook.katana": "페이스북",
    "org.telegram.messenger": "텔레그램",
    "com.tencent.tmgp.pubgmhd": "배틀그라운드 모바일",
    "com.supercell.brawlstars": "브롤스타즈",
    "com.supercell.clashofclans": "클래시 오브 클랜",
    "com.netmarble.sololv": "나 혼자만 레벨업: 어라이즈",
    "com.nexon.bluearchive": "블루 아카이브",
    "com.nexon.maplesorce": "메이플스토리M",
    "com.kakaogames.twinstar": "우마무스메",
    "com.kakaogames.rom": "ROM: 리멤버 오브 마제스티",
    "com.kakaogames.odin": "오딘: 발할라 라이징",
    "com.kakaogames.ares": "아레스: 라이즈 오브 가디언즈",
    "com.smilegate.megaport.stove": "STOVE",
    "com.riotgames.legendsofruneterra": "레전드 오브 룬테라",
    "com.riotgames.league.wildrift": "와일드 리프트",
    "com.riotgames.league.teamfighttactics": "TFT (전략적 팀 전투)",
    "com.miHoYo.GenshinImpact": "원신",
    "com.HoYoverse.hkrpgoversea": "붕괴: 스타레일",
    "com.HoYoverse.nap.open": "젠레스 존 제로",
    "com.devsisters.ck": "쿠키런: 킹덤",
    "com.devsisters.ca": "쿠키런: 오븐브레이크",
    "com.wemade.nightcrows": "나이트 크로우",
    "com.linegames.ud": "언디셈버",
    "com.sec.android.app.camera": "카메라",
    "com.android.settings": "설정",
    "com.sec.android.app.gallery": "갤러리",
    "com.sec.android.gallery3d": "갤러리",
    "com.samsung.android.app.contacts": "연락처",
    "com.samsung.android.messaging": "메시지",
    "com.android.chrome": "크롬 브라우저",
    "com.sec.android.app.clockpackage": "시계",
    "com.samsung.android.calendar": "캘린더",
    "com.sec.android.app.popupcalculator": "계산기",
    "com.samsung.android.app.notes": "삼성 노트",
    "com.sec.android.app.music": "삼성 뮤직",
    "com.samsung.android.oneconnect": "SmartThings",
    "com.samsung.android.voc": "삼성 멤버스",
    "com.samsung.android.app.files": "내 파일",
    "com.samsung.android.lool": "디바이스 케어",
    "com.samsung.android.knox.containeragent": "보안 폴더",
    "com.samsung.android.app.routines": "모드 및 루틴",
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
            lambda e: self.canvas.configure(scrollregion=self.canvas.boundingbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
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
            text="테두리 없는 전체화면`n(Borderless Fullscreen)", 
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
            # Find USB device
            stdout, _, _ = run_cmd([ADB_PATH, "devices"])
            usb_dev = None
            for line in stdout.splitlines():
                if "List of devices attached" in line or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    d_id = parts[0]
                    if ":" not in d_id and "192.168" not in d_id:
                        usb_dev = d_id
                        break
            
            if not usb_dev:
                def err():
                    self.btn_auto.config(state=tk.NORMAL)
                    messagebox.showerror("오류", "USB로 연결된 스마트폰을 감지할 수 없습니다. 케이블 연결을 확인해 주세요.")
                    self.set_status("USB 기기 없음", "red")
                self.root.after(0, err)
                return
            
            # Setup tcpip
            run_cmd([ADB_PATH, "-s", usb_dev, "tcpip", "5555"])
            
            # Fetch IP
            ip_stdout, _, _ = run_cmd([ADB_PATH, "-s", usb_dev, "shell", "ip route"])
            phone_ip = None
            for line in ip_stdout.splitlines():
                if "wlan0" in line and "src" in line:
                    m = re.search(r"src\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
                    if m:
                        phone_ip = m.group(1)
                        break
            
            if not phone_ip:
                # Try fallback
                ip_stdout, _, _ = run_cmd([ADB_PATH, "-s", usb_dev, "shell", "ip -o -4 addr show wlan0"])
                m = re.search(r"inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", ip_stdout)
                if m:
                    phone_ip = m.group(1)
            
            if not phone_ip:
                def ip_err():
                    self.btn_auto.config(state=tk.NORMAL)
                    messagebox.showerror("오류", "기기 Wi-Fi IP 주소를 파악할 수 없습니다.")
                    self.set_status("IP 획득 실패", "red")
                self.root.after(0, ip_err)
                return
            
            # Connect
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
            if not os.path.exists(icon_path):
                icon_path = DEFAULT_ICON_PNG
                
            # Create Tkinter PhotoImage card
            try:
                pil_img = Image.open(icon_path).resize((48, 48), Image.Resampling.LANCEWOOD)
                img = ImageTk.PhotoImage(pil_img)
            except Exception:
                # Fallback in case of PIL errors
                img = None

            # Card outer frame
            card = ttk.Frame(self.scrollable_frame, style="Card.TFrame", padding=5, borderwidth=1, relief="solid")
            card.grid(row=index // 3, column=index % 3, padx=8, pady=8, sticky="nsew")
            
            # Prevent image from garbage collection
            card.image = img
            
            # Elements inside card
            lbl_icon = ttk.Label(card, image=img)
            lbl_icon.pack(pady=(5, 2))
            
            lbl_name = ttk.Label(card, text=name, font=("Malgun Gothic", 9, "bold"), width=15, anchor="center", justify=tk.CENTER)
            lbl_name.pack(pady=(0, 2))
            
            lbl_pkg = ttk.Label(card, text=pkg, font=("Malgun Gothic", 7), foreground="gray", width=18, anchor="center")
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
        list_win.geometry("500x480")
        list_win.resizable(False, False)
        list_win.grab_set()
        
        # Search Entry Row
        search_row = ttk.Frame(list_win, padding="10")
        search_row.pack(fill=tk.X)
        
        ttk.Label(search_row, text="검색어:").pack(side=tk.LEFT, padx=(0, 5))
        search_var = tk.StringVar()
        entry_search = ttk.Entry(search_row, textvariable=search_var)
        entry_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        entry_search.focus()
        
        # Treeview to display list
        tree_frame = ttk.Frame(list_win, padding="10")
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        cols = ("Name", "Package")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)
        tree.heading("Name", text="앱 이름")
        tree.heading("Package", text="패키지명 (ID)")
        tree.column("Name", width=180)
        tree.column("Package", width=280)
        
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate List
        def populate(filter_str=""):
            # Clear tree
            for item in tree.get_children():
                tree.delete(item)
            # Add matching
            for app in self.all_apps:
                pkg = app["package"]
                # Resolve current label dynamically (helps pick up scraped labels)
                lbl = self.resolve_app_label_locally(pkg)
                app["label"] = lbl  # Keep local all_apps record updated
                
                if filter_str.lower() in lbl.lower() or filter_str.lower() in pkg.lower():
                    # Check if already added
                    suffix = ""
                    if any(x["package"] == pkg for x in self.favorites):
                        suffix = " (등록됨)"
                    tree.insert("", tk.END, values=(lbl + suffix, pkg))
                    
        populate()
        search_var.bind("<KeyRelease>", lambda e: populate(search_var.get()))
        
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
        
        # Start background async scrapings for missing items
        self.start_async_label_scraping(tree, list_win)

    def start_async_label_scraping(self, tree, list_win):
        def scrape_worker():
            updated_any = False
            # Filter packages that need scraping
            to_scrape = []
            for app in self.all_apps:
                pkg = app["package"]
                if pkg not in COMMON_APP_NAMES and pkg not in self.app_labels_cache:
                    to_scrape.append(app)
            
            # Scrape them one by one
            for app in to_scrape:
                # Stop if window is closed
                if not list_win.winfo_exists():
                    break
                    
                pkg = app["package"]
                scraped_label = self.scrape_play_store_label(pkg)
                if scraped_label:
                    self.app_labels_cache[pkg] = scraped_label
                    app["label"] = scraped_label
                    updated_any = True
                    
                    # Update Treeview in main thread
                    def update_ui(p=pkg, l=scraped_label):
                        try:
                            for item in tree.get_children():
                                values = tree.item(item, "values")
                                if values and values[1] == p:
                                    suffix = " (등록됨)" if any(x["package"] == p for x in self.favorites) else ""
                                    tree.set(item, "Name", l + suffix)
                                    break
                        except Exception:
                            pass
                    self.root.after(0, update_ui)
                    
            if updated_any:
                self.save_app_labels_cache()
                
        threading.Thread(target=scrape_worker, daemon=True).start()

    # ----------------------------------------------------
    # High-speed asynchronous app icon extraction (unzip logic)
    # ----------------------------------------------------
    def extract_app_icon(self, dev_id, pkg, label):
        def run():
            local_png = os.path.join(ICON_CACHE_DIR, f"{pkg}.png")
            local_ico = os.path.join(ICON_CACHE_DIR, f"{pkg}.ico")
            
            # 1. Fetch APK Path on the phone
            stdout, _, _ = run_cmd([ADB_PATH, "-s", dev_id, "shell", f"pm path {pkg}"])
            apk_path = None
            for line in stdout.splitlines():
                if line.startswith("package:"):
                    apk_path = line.replace("package:", "").strip()
                    break
            
            success = False
            if apk_path:
                # 2. Query zip contents of the APK for icon file name
                # Usually icons are stored under res/mipmap-*/ic_launcher.png
                stdout, _, _ = run_cmd([ADB_PATH, "-s", dev_id, "shell", f"unzip -l {apk_path}"])
                icon_file = None
                
                # Check for standard launcher icons
                candidates = []
                for line in stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 4:
                        filename = parts[3]
                        if "ic_launcher" in filename and filename.endswith(".png"):
                            candidates.append(filename)
                
                # Sort candidates to find the highest resolution (xxxhdpi, etc.)
                if candidates:
                    candidates.sort() # lexicographical sorting helps prioritize higher density folders like xxxhdpi
                    icon_file = candidates[-1]
                else:
                    # Generic fallback: Search any icon.png
                    for line in stdout.splitlines():
                        parts = line.split()
                        if len(parts) >= 4:
                            filename = parts[3]
                            if filename.endswith(".png") and ("icon" in filename.lower() or "logo" in filename.lower()):
                                icon_file = filename
                                break
                                
                if icon_file:
                    # 3. Decompress the single icon file to temp folder inside the phone
                    temp_phone_path = "/data/local/tmp/icon_temp.png"
                    run_cmd([ADB_PATH, "-s", dev_id, "shell", f"unzip -p {apk_path} {icon_file} > {temp_phone_path}"])
                    
                    # 4. Pull to PC cache
                    pull_stdout, pull_stderr, code = run_cmd([ADB_PATH, "-s", dev_id, "pull", temp_phone_path, local_png])
                    if code == 0 and os.path.exists(local_png):
                        success = True
                    
                    # 5. Clean phone temp folder
                    run_cmd([ADB_PATH, "-s", dev_id, "shell", f"rm {temp_phone_path}"])

            # 6. Convert to ICO if extraction succeeded
            if success:
                try:
                    img = Image.open(local_png)
                    # Convert to ICO
                    img.save(local_ico, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
                except Exception as e:
                    print("ICO Conversion failed:", e)
            else:
                # If failed, copy default launcher icons
                if os.path.exists(DEFAULT_ICON_PNG):
                    try:
                        import shutil
                        shutil.copyfile(DEFAULT_ICON_PNG, local_png)
                        shutil.copyfile(DEFAULT_ICON_ICO, local_ico)
                    except:
                        pass
            
            # Reload GUI
            self.root.after(0, lambda: self.finish_icon_extraction(label))
            
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
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                html = response.read().decode('utf-8', errors='ignore')
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
