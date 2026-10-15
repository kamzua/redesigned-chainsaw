import time
import json
import os
import re
import csv
import shutil
import traceback
import platform
import sqlite3
import sys
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import threading
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

EXCLUDE_WORDS = {
    "DAILY", "LOGIN", "BODY", "EVENT", "AUDITION", "PLAYPARK", "HEADER", "FOOTER",
    "CONTAINER", "WRAPPER", "BANNER", "BUTTON", "CENTER", "SELECT", "GAME", "ITEM",
    "CODE", "MENU", "NOTICE", "NEWS", "REGISTER", "FACEBOOK", "PLAYID", "SUBMIT"
}

DAILY_LOGIN_URL_DEFAULT = "https://audition.playpark.com/th-th/news/daily-login-october-2026/"

ITEM_CODE_REWARDS = {
    "CFE-FE5-E548A83": {"day": 1, "name": "ทรงผม Youth Confidence/Catch Me (15 วัน)"},
    "B3C-3C4-C42AFD0": {"day": 2, "name": "เสื้อ Youth Confidence/Catch Me (15 วัน)"},
    "9BD-3D8-D855667": {"day": 3, "name": "กางเกง Youth Confidence/Catch Me (15 วัน)"},
    "B0A-0AB-ABF2D8E": {"day": 4, "name": "รองเท้า Youth Confidence/Catch Me (15 วัน)"},
    "817-171-7121941": {"day": 5, "name": "ปีก Charisma Black Wings (15 วัน)"},
    "840-40F-0F65F9A": {"day": 6, "name": "ไอเทม/แว่น Cacao Creme Kiwi (15 วัน)"},
    "FD3-D34-34ECB1A": {"day": 7, "name": "ทรงผม Pastel Punk/Sour Flower (ถาวร)"},
    "C20-B03-03D5032": {"day": 8, "name": "หน้า Red Eye Bad Boy/Girl Face (15 วัน)"},
    "3E0-E02-026DADA": {"day": 9, "name": "ทรงผม Fresh College Student Couple (15 วัน)"},
    "D8E-8EE-EEB20AC": {"day": 10, "name": "เสื้อ Fresh College Student Couple (15 วัน)"},
}

def get_item_name_for_code(code):
    return ITEM_CODE_REWARDS.get((code or "").strip().upper(), {}).get("name", "")

DAILY_REWARD_NAMES = {
    1: "ทรงผม Youth Confidence/Catch Me (15 วัน)",
    2: "เสื้อ Youth Confidence/Catch Me (15 วัน)",
    3: "กางเกง Youth Confidence/Catch Me (15 วัน)",
    4: "รองเท้า Youth Confidence/Catch Me (15 วัน)",
    5: "ปีก Charisma Black Wings (15 วัน)",
    6: "ไอเทม Cacao Creme Kiwi (15 วัน)",
    7: "ทรงผม Pastel Punk/Sour Flower (ถาวร)",
    8: "หู Red Eye Bad Boy/Girl Face (15 วัน)",
    9: "กระเป๋า Fresh College Student Couple (15 วัน)",
    10: "เสื้อ Fresh College Student Couple (15 วัน)",
    11: "กางเกง Fresh College Student Couple (15 วัน)",
    12: "รองเท้า Fresh College Student Couple (15 วัน)",
    13: "สัตว์เลี้ยง Windy Hallow (15 วัน)",
    14: "รองเท้า Pastel Punk/Sour Flower (ถาวร)",
    15: "ทรงผม Youth Confidence/Catch Me (15 วัน)",
    16: "เสื้อ Youth Confidence/Catch Me (15 วัน)",
    17: "กางเกง Youth Confidence/Catch Me (15 วัน)",
    18: "รองเท้า Youth Confidence/Catch Me (15 วัน)",
    19: "ปีก Charisma Black Wings (15 วัน)",
    20: "ไอเทม Cacao Creme Kiwi (15 วัน)",
    21: "กางเกง Pastel Punk/Sour Flower (ถาวร)",
    22: "หู Red Eye Bad Boy/Girl Face (15 วัน)",
    23: "กระเป๋า Fresh College Student Couple (15 วัน)",
    24: "เสื้อ Fresh College Student Couple (15 วัน)",
    25: "กางเกง Fresh College Student Couple (15 วัน)",
    26: "รองเท้า Fresh College Student Couple (15 วัน)",
    27: "สัตว์เลี้ยง Windy Hallow (15 วัน)",
    28: "เสื้อ Pastel Punk/Sour Flower (ถาวร)",
}

def daily_reward_name(day_num):
    try:
        return DAILY_REWARD_NAMES.get(int(day_num), "")
    except (TypeError, ValueError):
        return ""

def extract_daily_reward_labels(driver):
    labels = []
    try:
        payload = driver.execute_script("""
            const out = [];
            const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
            document.querySelectorAll('img').forEach(img => {
                if (!visible(img)) return;
                const bits = [img.alt, img.title, img.getAttribute('aria-label')].filter(Boolean);
                if (bits.length) out.push(...bits);
            });
            document.querySelectorAll('[aria-label], [title]').forEach(el => {
                if (!visible(el)) return;
                const t = el.getAttribute('aria-label') || el.getAttribute('title');
                if (t && t.length < 180) out.push(t);
            });
            return {text: document.body ? document.body.innerText : '', labels: out};
        """)
        visible_text = payload.get("text", "") or ""
        raw_labels = payload.get("labels", []) or []
        candidates = list(raw_labels)
        for line in visible_text.splitlines():
            line = line.strip(" •\\t-–—:")
            if not line or len(line) > 140:
                continue
            if re.search(r'\b(item|ไอเทม|ไอเท็ม|ผู้ชาย|ผู้หญิง|couple|style|punk|fashion|star|date)\b', line, re.I):
                candidates.append(line)
        seen = set()
        for value in candidates:
            value = re.sub(r'\s+', ' ', str(value)).strip()
            if not value or len(value) > 140:
                continue
            if value.lower() in seen:
                continue
            if re.search(r'(daily login|playpark|audition เกม|อ่านเพิ่มเติม|หน้าแรก|image:)', value, re.I):
                continue
            seen.add(value.lower())
            labels.append(value)
    except Exception:
        pass
    return labels

def is_valid_item_code(code_str):
    if not code_str:
        return False
    upper_code = code_str.upper().strip()
    parts = upper_code.split('-')
    if len(parts) < 3:
        return False
    for part in parts:
        if part in EXCLUDE_WORDS:
            return False
    return True

def parse_accounts(text):
    accounts = []
    lines = [line.strip() for line in (text or "").strip().splitlines() if line.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if "|" in line:
            user, password = line.split("|", 1)
            user, password = user.strip(), password.strip()
            if user and password:
                accounts.append((user, password))
            i += 1
            continue
        if "\t" in line:
            parts = [part.strip() for part in line.split("\t", 1)]
        else:
            parts = line.split()
        if len(parts) >= 2:
            accounts.append((parts[0], parts[1]))
            i += 1
        else:
            user = line
            password = lines[i + 1] if i + 1 < len(lines) else ""
            if password:
                accounts.append((user, password))
            i += 2
    return accounts

def send_discord_webhook(webhook_url, message):
    if not webhook_url or not webhook_url.startswith("http"):
        return
    try:
        data = json.dumps({"content": message}).encode("utf-8")
        req = urllib.request.Request(
            webhook_url, 
            data=data, 
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print("Discord Webhook Error:", e)

def show_readable_alert(parent, title, message, kind="info"):
    try:
        win = tk.Toplevel(parent)
        win.title(title)
        win.configure(bg="#fff4fa")
        win.transient(parent)
        win.resizable(True, True)
        win.minsize(760, 460)
        width = 980
        height = 620
        win.update_idletasks()
        x = parent.winfo_rootx() + max(20, (parent.winfo_width() - width) // 2)
        y = parent.winfo_rooty() + max(20, (parent.winfo_height() - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

        accent = {"error": "#b91c1c", "warning": "#92400e", "info": "#7e2257"}.get(kind, "#7e2257")
        symbol = {"error": "❗", "warning": "⚠", "info": "💗"}.get(kind, "💗")
        header = tk.Frame(win, bg=accent, padx=18, pady=14)
        header.pack(fill="x")
        tk.Label(header, text=f"{symbol}  {title}", bg=accent, fg="#ffffff",
                 font=("Segoe UI", 20, "bold"), anchor="w", justify="left",
                 wraplength=700).pack(fill="x")

        body = tk.Frame(win, bg="#fff4fa", padx=18, pady=16)
        body.pack(fill="both", expand=True)
        text = scrolledtext.ScrolledText(
            body, wrap="word", font=("Segoe UI", 16), bg="#ffffff", fg="#201326",
            insertbackground="#201326", relief="solid", bd=1, padx=12, pady=10,
            highlightthickness=1, highlightbackground="#d18ab2"
        )
        text.pack(fill="both", expand=True)
        text.insert("1.0", str(message))
        text.configure(state="disabled")

        footer = tk.Frame(win, bg="#fff4fa", padx=18, pady=(0, 16))
        footer.pack(fill="x")
        btn = tk.Button(footer, text="ตกลง", command=win.destroy,
                        font=("Segoe UI", 15, "bold"), bg="#9d174d", fg="#ffffff",
                        activebackground="#7e2257", activeforeground="#ffffff",
                        relief="flat", padx=30, pady=8, cursor="hand2")
        btn.pack(side="right")
        win.bind("<Return>", lambda _e: win.destroy())
        win.bind("<Escape>", lambda _e: win.destroy())
        win.grab_set()
        win.focus_force()
        btn.focus_set()
        parent.wait_window(win)
    except tk.TclError:
        pass

class AuditionDailyLoginBot:
    def __init__(self, root):
        self.root = root
        self.root.title("AUDITION ♡ SWEET DREAMS • Daily Login & Item Code")
        self.root.update_idletasks()
        screen_w, screen_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        win_w, win_h = min(1500, max(900, screen_w - 80)), min(1000, max(650, screen_h - 100))
        self.root.geometry(f"{win_w}x{win_h}+10+10")
        self.root.minsize(760, 560)
        self.colors = {
            "bg": "#fff4fa", "panel": "#ffffff", "panel2": "#f7c3df",
            "text": "#201326", "muted": "#392842", "cyan": "#075985",
            "pink": "#9d174d", "purple": "#5b21b6", "green": "#065f46",
            "red": "#9f1239", "input": "#ffffff", "border": "#c76a9f"
        }
        c = self.colors
        self.root.configure(bg=c["bg"])
        self.root.option_add("*Font", ("Segoe UI", 12))
        self.root.option_add("*Background", c["panel"])
        self.root.option_add("*Foreground", c["text"])
        self.root.option_add("*Entry.Background", c["input"])
        self.root.option_add("*Entry.Foreground", c["text"])
        self.root.option_add("*Entry.InsertBackground", c["cyan"])
        self.root.option_add("*Text.Background", c["input"])
        self.root.option_add("*Text.Foreground", c["text"])
        self.root.option_add("*Text.InsertBackground", c["cyan"])
        self.root.option_add("*Checkbutton.Background", c["panel"])
        self.root.option_add("*Checkbutton.Foreground", c["text"])
        self.root.option_add("*Checkbutton.SelectColor", c["panel2"])
        self.root.option_add("*Label.Background", c["bg"])
        self.root.option_add("*Label.Foreground", c["text"])
        self.root.option_add("*LabelFrame.Background", c["panel"])
        self.root.option_add("*LabelFrame.Foreground", c["pink"])
        self.root.option_add("*Button.Font", ("Segoe UI", 11, "bold"))
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=c["bg"])
        style.configure("TNotebook", background=c["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=c["panel2"], foreground=c["text"], padding=(18, 10), font=("Segoe UI", 12, "bold"))
        style.map("TNotebook.Tab", background=[("selected", c["pink"])], foreground=[("selected", "#ffffff")])
        style.configure("Treeview", background=c["input"], fieldbackground=c["input"], foreground=c["text"], rowheight=36, bordercolor=c["border"])
        style.configure("Treeview.Heading", background=c["panel2"], foreground=c["text"], font=("Segoe UI", 11, "bold"), padding=10)
        style.map("Treeview", background=[("selected", c["purple"])], foreground=[("selected", "#ffffff")])
        self.is_running = False

        control_bar = tk.Frame(root, bg=self.colors["bg"])
        control_bar.pack(side="top", fill="x", padx=10, pady=(8, 2))
        self.btn_start = tk.Button(
            control_bar, text="♡  เริ่มทำงาน  •  F8", bg=self.colors["green"], fg="#ffffff",
            activebackground=self.colors["purple"], activeforeground="#ffffff",
            relief="flat", bd=0, padx=12, pady=10,
            font=("Segoe UI", 12, "bold"), command=self.start_process
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.btn_stop = tk.Button(
            control_bar, text="■  หยุด  •  F9", bg=self.colors["red"], fg="#ffffff",
            activebackground=self.colors["pink"], activeforeground="#ffffff",
            relief="flat", bd=0, padx=16, pady=10,
            font=("Segoe UI", 12, "bold"), state="disabled", command=self.stop_process
        )
        self.btn_stop.pack(side="right", padx=(5, 0))
        self.root.bind_all("<F8>", self._hotkey_start)
        self.root.bind_all("<F9>", self._hotkey_stop)

        progress_frame = tk.Frame(root, bg=self.colors["bg"])
        progress_frame.pack(side="top", fill="x", padx=12, pady=(0, 4))
        self.progress_text = tk.StringVar(value="พร้อมทำงาน • ยังไม่มีงานที่กำลังดำเนินการ")
        tk.Label(progress_frame, textvariable=self.progress_text, bg=self.colors["bg"],
                 fg=self.colors["text"], anchor="w").pack(fill="x")
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate", maximum=100, value=0)
        self.progress_bar.pack(fill="x", pady=(2, 0))
        self.resume_completed_accounts = set()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=6)
        main_page_container = ttk.Frame(self.notebook)
        accounts_page = ttk.Frame(self.notebook)
        history_page = ttk.Frame(self.notebook)
        self.notebook.add(main_page_container, text="หน้าหลัก")
        
        main_canvas = tk.Canvas(main_page_container, bg=self.colors["bg"], highlightthickness=0)
        main_vscroll = ttk.Scrollbar(main_page_container, orient="vertical", command=main_canvas.yview)
        main_canvas.configure(yscrollcommand=main_vscroll.set)
        main_vscroll.pack(side="right", fill="y")
        main_canvas.pack(side="left", fill="both", expand=True)
        main_page = ttk.Frame(main_canvas)
        main_window_id = main_canvas.create_window((0, 0), window=main_page, anchor="nw")
        main_page.bind("<Configure>", lambda _e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
        main_canvas.bind("<Configure>", lambda e: main_canvas.itemconfigure(main_window_id, width=e.width))
        def _main_mousewheel(event):
            try:
                main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except (AttributeError, tk.TclError):
                pass
        main_canvas.bind_all("<MouseWheel>", _main_mousewheel)
        self.notebook.add(accounts_page, text="บัญชี ID / Password")
        self.notebook.add(history_page, text="ประวัติย้อนหลัง")
        self.accounts_page = accounts_page
        self.history_page = history_page
        
        self.is_pass_visible = True
        self.actual_accounts_text = ""
        self.account_results = {}
        self.last_notification = ""

        tk.Label(main_page, text="♡  AUDITION SWEET DREAMS  ♡", font=("Segoe UI", 22, "bold"), bg=self.colors["bg"], fg=self.colors["pink"]).pack(pady=(12, 2))
        tk.Label(main_page, text="DAILY LOGIN  ✧  ITEM CODE  ✧  ACCOUNT MANAGER", font=("Segoe UI", 12, "bold"), bg=self.colors["bg"], fg=self.colors["purple"]).pack(pady=(0, 8))
        self.notify_label = tk.Label(
            main_page, text="●  READY  —  ผลการทำงานจะแสดงตรงนี้",
            font=("Segoe UI", 16, "bold"), bg=self.colors["panel2"], fg=self.colors["cyan"],
            anchor="w", justify="left", wraplength=1080, padx=14, pady=12,
            height=2
        )
        self.notify_label.pack(fill="x", padx=10, pady=(0, 8))

        url_frame = tk.LabelFrame(main_page, text=" 01  /  DAILY LOGIN  •  ลิงก์กิจกรรม ", padx=10, pady=7, bg=self.colors["panel"], fg=self.colors["cyan"], bd=1, relief="groove")
        url_frame.pack(fill="x", padx=10, pady=2)

        self.do_daily_login = tk.BooleanVar(value=True)
        chk_daily = tk.Checkbutton(url_frame, text="เปิดใช้งานระบบ Daily Login (กดรับแต้ม + ดึงโค้ด)", variable=self.do_daily_login, font=("Segoe UI", 12, "bold"), fg=self.colors["green"])
        chk_daily.pack(anchor="w")

        self.run_headless = tk.BooleanVar(value=True)
        chk_headless = tk.Checkbutton(
            url_frame,
            text="ทำงานเบื้องหลัง ไม่แย่งเมาส์ (Headless Chrome)",
            variable=self.run_headless,
            font=("Segoe UI", 12),
            fg=self.colors["cyan"]
        )
        chk_headless.pack(anchor="w")

        self.txt_url = tk.Entry(url_frame, font=("Segoe UI", 12))
        self.txt_url.insert(0, "https://audition.playpark.com/th-th/news/daily-login-october-2026/")
        self.txt_url.pack(fill="x", pady=2)
        tk.Button(
            url_frame, text="💾 บันทึกลิงก์ Daily Login",
            command=self.save_link_settings, bg=self.colors["green"], fg="#ffffff",
            activebackground=self.colors["purple"], relief="flat", padx=12, pady=5
        ).pack(anchor="e", pady=(2, 0))

        code_frame = tk.LabelFrame(main_page, text=" 02  /  ITEM CODE  •  เติมไอเทม ", padx=10, pady=7, bg=self.colors["panel"], fg=self.colors["pink"], bd=1, relief="groove")
        code_frame.pack(fill="x", padx=10, pady=3)

        code_hdr = tk.Frame(code_frame)
        code_hdr.pack(fill="x")

        self.do_redeem_code = tk.BooleanVar(value=True)
        chk_code = tk.Checkbutton(code_hdr, text="เปิดใช้งานระบบเติม Item Code อัตโนมัติ", variable=self.do_redeem_code, font=("Segoe UI", 12, "bold"), fg=self.colors["pink"])
        chk_code.pack(side="left")

        self.only_permanent_items = tk.BooleanVar(value=False)
        chk_permanent = tk.Checkbutton(
            code_frame,
            text="เติมเฉพาะไอเทมถาวร (Day 7, 14, 21, 28) — ข้ามไอเทมแบบมีวันหมดอายุ",
            variable=self.only_permanent_items,
            font=("Segoe UI", 12, "bold"),
            fg=self.colors["purple"]
        )
        chk_permanent.pack(anchor="w")

        tk.Label(code_frame, text="ลิงก์หน้าเติมโค้ด (PlayPark Item Code URL):", font=("Segoe UI", 12)).pack(anchor="w")
        self.txt_code_url = tk.Entry(code_frame, font=("Segoe UI", 12))
        self.txt_code_url.insert(0, "https://secure2.playpark.com/itemcode/AUItemCode/AuLogin.aspx")
        self.txt_code_url.pack(fill="x", pady=2)
        tk.Button(
            code_frame, text="💾 บันทึกลิงก์หน้าเติมโค้ด",
            command=self.save_link_settings, bg=self.colors["green"], fg="#ffffff",
            activebackground=self.colors["purple"], relief="flat", padx=12, pady=5
        ).pack(anchor="e", pady=(2, 0))

        tk.Label(code_frame, text="รหัส Item Code สำรองเพิ่มเติม (ใส่หรือไม่ใส่ก็ได้):", font=("Segoe UI", 12)).pack(anchor="w")
        self.txt_item_codes = scrolledtext.ScrolledText(code_frame, height=3, font=("Cascadia Mono", 11), bg=self.colors["input"], fg=self.colors["text"], insertbackground=self.colors["cyan"], relief="flat", bd=2)
        self.txt_item_codes.pack(fill="x", pady=2)

        tk.Label(
            self.accounts_page,
            text="กรอกรายการบัญชีสำหรับระบบ Daily Login และ Item Code",
            font=("Segoe UI", 11, "bold"),
            fg=self.colors["cyan"]
        ).pack(anchor="w", padx=12, pady=(12, 4))
        acc_frame = tk.LabelFrame(self.accounts_page, text=" ACCOUNT VAULT  /  รายการไอดี ", padx=10, pady=10, bg=self.colors["panel"], fg=self.colors["cyan"], bd=1, relief="groove")
        acc_frame.pack(fill="both", expand=True, padx=10, pady=3)

        acc_header = tk.Frame(acc_frame)
        acc_header.pack(fill="x", pady=(0, 4))
        
        tk.Label(acc_header, text="กรอกหลายบัญชีได้: ID PASSWORD หรือ ID|PASSWORD (1 บัญชีต่อ 1 บรรทัด)", font=("Segoe UI", 12), fg="#302136").pack(side="left")
        
        tk.Label(
            acc_frame,
            text="ตัวอย่าง:\naccount01 password01\naccount02|password02\nหรือใส่ ID และ Password คนละบรรทัดก็ได้",
            font=("Consolas", 12), fg="#302136", justify="left", anchor="w"
        ).pack(fill="x", padx=4, pady=(0, 4))

        self.btn_toggle_pass = tk.Button(
            acc_header, 
            text="👁️ ซ่อน ID/รหัสผ่าน", 
            font=("Segoe UI", 12, "bold"), 
            bg=self.colors["panel2"], fg=self.colors["cyan"], activebackground=self.colors["purple"], relief="flat", bd=0, padx=8, pady=5,
            command=self.toggle_password_visibility
        )
        self.btn_toggle_pass.pack(side="right")

        self.btn_load_accounts = tk.Button(
            acc_header,
            text="📂 โหลดบัญชีจากไฟล์ .txt",
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["panel2"], fg=self.colors["text"], activebackground=self.colors["purple"], relief="flat", bd=0, padx=8, pady=5,
            command=self.load_accounts_file
        )
        self.btn_load_accounts.pack(side="right", padx=(0, 6))

        self.txt_accounts = scrolledtext.ScrolledText(acc_frame, height=9, font=("Cascadia Mono", 11), bg=self.colors["input"], fg=self.colors["text"], insertbackground=self.colors["cyan"], relief="flat", bd=2)
        self.txt_accounts.pack(fill="both", expand=True)
        
        self.settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audition_bot_settings.json")
        self.txt_accounts.bind("<KeyRelease>", self.save_settings)
        self.load_settings()

        webhook_frame = tk.LabelFrame(main_page, text=" 03  /  DISCORD NOTIFICATIONS ", padx=10, pady=7, bg=self.colors["panel"], fg=self.colors["purple"], bd=1, relief="groove")
        webhook_frame.pack(fill="x", padx=10, pady=2)

        self.txt_webhook = tk.Entry(webhook_frame, font=("Segoe UI", 12))
        self.txt_webhook.pack(fill="x", pady=2)

        log_frame = tk.LabelFrame(main_page, text=" LIVE CONSOLE  /  สถานะการทำงาน ", padx=10, pady=8, bg=self.colors["panel"], fg=self.colors["green"], bd=1, relief="groove")
        log_frame.pack(fill="both", expand=True, padx=10, pady=3)
        self.txt_log = scrolledtext.ScrolledText(log_frame, height=11, font=("Cascadia Mono", 14), bg="#17101d", fg="#d7ffe9", insertbackground=self.colors["cyan"], relief="flat", bd=2, padx=8, pady=8, spacing1=2, spacing3=2)

        self.txt_log.pack(fill="both", expand=True)

        reward_frame = tk.LabelFrame(main_page, text=" REWARD TRACKER  /  DAILY LOGIN 28 วัน ", padx=10, pady=8, bg=self.colors["panel"], fg=self.colors["purple"], bd=1, relief="groove")
        reward_frame.pack(fill="both", expand=True, padx=10, pady=3)
        self.reward_status = tk.Label(
            reward_frame,
            text="ยังไม่ได้อ่านข้อมูลจากหน้าเว็บ — กดเริ่มระบบเพื่ออ่านชื่อที่หน้าเว็บเปิดเผย",
            anchor="w", justify="left", wraplength=680, fg="#302136"
        )
        self.reward_status.pack(fill="x", pady=(0, 4))
        columns = ("day", "item", "source")
        self.reward_tree = ttk.Treeview(reward_frame, columns=columns, show="headings", height=7)
        self.reward_tree.heading("day", text="วัน")
        self.reward_tree.heading("item", text="ชื่อไอเทมจากเว็บ")
        self.reward_tree.heading("source", text="สถานะข้อมูล")
        self.reward_tree.column("day", width=55, anchor="center")
        self.reward_tree.column("item", width=400)
        self.reward_tree.column("source", width=160)
        self.reward_tree.pack(fill="both", expand=True)
        for day in range(1, 29):
            self.reward_tree.insert("", "end", iid=f"day{day}", values=(f"Day {day}", "ยังไม่พบชื่อไอเทม", "รออ่านจากเว็บ"))

        history_header = tk.Frame(self.history_page, bg=self.colors["bg"])
        history_header.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(history_header, text="♡ ประวัติ Daily Login + Item Code ย้อนหลัง", font=("Segoe UI", 18, "bold"),
                 bg=self.colors["bg"], fg=self.colors["pink"]).pack(side="left")
        history_actions = tk.Frame(self.history_page, bg=self.colors["bg"])
        history_actions.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(history_actions, text="ค้นหาไอดี / โค้ด / สถานะ:", bg=self.colors["bg"], fg=self.colors["text"]).pack(side="left")
        self.history_search_var = tk.StringVar()
        self.history_search_entry = tk.Entry(history_actions, textvariable=self.history_search_var, font=("Segoe UI", 12), width=30)
        self.history_search_entry.pack(side="left", padx=6)
        self.history_search_entry.bind("<KeyRelease>", lambda _e: self.refresh_history())
        tk.Label(history_actions, text="สถานะ:", bg=self.colors["bg"], fg=self.colors["text"]).pack(side="left", padx=(8, 2))
        self.history_status_filter = tk.StringVar(value="ทั้งหมด")
        self.history_status_combo = ttk.Combobox(history_actions, textvariable=self.history_status_filter,
            values=("ทั้งหมด", "สำเร็จ", "โค้ดถูกใช้งานแล้ว", "ไม่สำเร็จ", "ยังยืนยันผลไม่ได้"),
            width=18, state="readonly")
        self.history_status_combo.pack(side="left", padx=3)
        self.history_status_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_history())
        tk.Label(history_actions, text="วันที่เริ่ม (YYYY-MM-DD):", bg=self.colors["bg"], fg=self.colors["text"]).pack(side="left", padx=(5, 2))
        self.history_date_from = tk.StringVar(value="")
        self.history_date_from_entry = tk.Entry(history_actions, textvariable=self.history_date_from, width=12)
        self.history_date_from_entry.pack(side="left", padx=2)
        self.history_date_from_entry.bind("<KeyRelease>", lambda _e: self.refresh_history())
        tk.Label(history_actions, text="ถึง:", bg=self.colors["bg"], fg=self.colors["text"]).pack(side="left", padx=(3, 2))
        self.history_date_to = tk.StringVar(value="")
        self.history_date_to_entry = tk.Entry(history_actions, textvariable=self.history_date_to, width=12)
        self.history_date_to_entry.pack(side="left", padx=2)
        self.history_date_to_entry.bind("<KeyRelease>", lambda _e: self.refresh_history())
        tk.Button(history_actions, text="ล้างตัวกรอง", command=self.clear_history_filters,
                  bg=self.colors["panel2"], fg=self.colors["text"], relief="flat", padx=8, pady=5).pack(side="left", padx=3)
        
        history_buttons = tk.Frame(self.history_page, bg=self.colors["bg"])
        history_buttons.pack(fill="x", padx=12, pady=(0, 8))
        tk.Button(history_buttons, text="🔄 รีเฟรช", command=self.refresh_history,
                  bg=self.colors["panel2"], fg=self.colors["text"], relief="flat", padx=10, pady=5).pack(side="left", padx=3)
        tk.Button(history_buttons, text="🗑 ลบรายการที่เลือก", command=self.delete_selected_history,
                  bg="#b4234d", fg="#ffffff", relief="flat", padx=10, pady=5).pack(side="left", padx=3)
        tk.Button(history_buttons, text="ล้างประวัติทั้งหมด", command=self.clear_all_history,
                  bg="#7f1d1d", fg="#ffffff", relief="flat", padx=10, pady=5).pack(side="left", padx=3)
        tk.Button(history_buttons, text="📤 ส่งออก CSV", command=self.export_history_csv,
                  bg=self.colors["green"], fg="#ffffff", relief="flat", padx=10, pady=5).pack(side="left", padx=3)
        tk.Button(history_buttons, text="💾 สำรองประวัติ", command=self.backup_history,
                  bg=self.colors["purple"], fg="#ffffff", relief="flat", padx=8, pady=5).pack(side="left", padx=3)
        tk.Button(history_buttons, text="♻️ กู้คืนประวัติ", command=self.restore_history,
                  bg=self.colors["purple"], fg="#ffffff", relief="flat", padx=8, pady=5).pack(side="left", padx=3)
        tk.Button(history_buttons, text="🧰 รายงานปัญหา", command=self.export_diagnostic_report,
                  bg=self.colors["panel2"], fg=self.colors["text"], relief="flat", padx=8, pady=5).pack(side="left", padx=3)
        tk.Button(history_buttons, text="📂 เปิดโฟลเดอร์ประวัติ", command=self.open_history_folder,
                  bg=self.colors["purple"], fg="#ffffff", relief="flat", padx=10, pady=5).pack(side="left", padx=3)
        
        history_note = tk.Label(self.history_page,
            text="บันทึกผลรับแต้ม Daily Login และผลเติม Item Code ไว้ร่วมกัน • ปิดแล้วเปิดใหม่ประวัติยังอยู่ • ไม่บันทึกรหัสผ่าน",
            bg=self.colors["bg"], fg=self.colors["muted"], anchor="w", font=("Segoe UI", 11))
        self.history_note = history_note
        history_note.pack(fill="x", padx=12, pady=(0, 6))
        
        history_frame = tk.Frame(self.history_page, bg=self.colors["panel"])
        history_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        hist_cols = ("time", "account", "code", "status", "item", "details")
        self.history_tree = ttk.Treeview(history_frame, columns=hist_cols, show="headings")
        headings = {"time":"วันและเวลา", "account":"ไอดีบัญชี", "code":"Item Code", "status":"สถานะ", "item":"ไอเทม", "details":"ข้อความจากเว็บ"}
        widths = {"time":155, "account":190, "code":155, "status":170, "item":260, "details":420}
        for col in hist_cols:
            self.history_tree.heading(col, text=headings[col])
            self.history_tree.column(col, width=widths[col], minwidth=90, stretch=(col in ("item", "details")))
        hist_y = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        hist_x = ttk.Scrollbar(history_frame, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=hist_y.set, xscrollcommand=hist_x.set)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        hist_y.grid(row=0, column=1, sticky="ns")
        hist_x.grid(row=1, column=0, sticky="ew")
        history_frame.rowconfigure(0, weight=1)
        history_frame.columnconfigure(0, weight=1)
        self.history_tree.bind("<Double-1>", self.open_history_detail)

        app_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
        self.history_db_path = os.path.join(app_dir, "audition_history.sqlite3")
        self.init_history_db()
        self.refresh_history()

    def _hotkey_start(self, event=None):
        if str(self.btn_start["state"]) != "disabled":
            self.start_process()
        return "break"

    def _hotkey_stop(self, event=None):
        if str(self.btn_stop["state"]) != "disabled":
            self.stop_process()
        return "break"

    def navigate_and_extract_codes(self, driver):
        codes = []
        try:
            clicked_history = False
            history_xpaths = [
                "//a[contains(@href, 'History') or contains(text(), 'ประวัติ')]",
                "//button[contains(text(), 'ประวัติ')]",
                "//*[contains(text(), 'ประวัติการรับรางวัล') or contains(text(), 'ประวัติกิจกรรม')]",
                "//img[contains(@src, 'btn_history') or contains(@src, 'history')]/.."
            ]

            for xp in history_xpaths:
                try:
                    btns = driver.find_elements(By.XPATH, xp)
                    for btn in btns:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            time.sleep(0.3)
                            driver.execute_script("arguments[0].click();", btn)
                            clicked_history = True
                            break
                    if clicked_history:
                        break
                except Exception:
                    pass

            if not clicked_history:
                driver.get("https://secure2.playpark.com/DailyLoginCenter/History.aspx")

            time.sleep(2.0)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.7)

            regex_pattern = r'\b[A-Za-z0-9]{3,5}-[A-Za-z0-9]{3,5}-[A-Za-z0-9]{4,10}\b'

            def scan_text(text):
                if not text:
                    return
                matches = re.findall(regex_pattern, text)
                for m in matches:
                    c = m.strip().upper()
                    if is_valid_item_code(c) and c not in codes:
                        codes.append(c)

            try:
                visible_text = driver.execute_script(
                    "return document.body ? document.body.innerText : '';"
                )
                scan_text(visible_text)
                self.log(f"🔎 ตรวจพบ Item Code จากข้อความที่มองเห็นบนหน้าเว็บ {len(codes)} โค้ด")
                if codes:
                    self.log("📋 รายการที่พบ: " + ", ".join(codes))
            except Exception as e:
                self.log(f"⚠️ อ่านข้อความที่มองเห็นบนหน้าเว็บไม่สำเร็จ: {str(e).splitlines()[0]}")

        except Exception as e:
            print("Extract codes error:", e)

        return codes

    def update_reward_table(self, names=None, source_note="อ้างอิงภาพรางวัลที่ผู้ใช้ส่งมา"):
        def apply():
            try:
                for day in range(1, 29):
                    self.reward_tree.item(
                        f"day{day}",
                        values=(f"Day {day}", daily_reward_name(day), source_note)
                    )
                self.reward_status.config(
                    text="ใส่ชื่อรางวัลตามภาพ Daily Login ที่ผู้ใช้ส่งมาแล้ว; ตรวจสอบชื่อจากภาพต้นฉบับได้",
                    fg=self.colors["cyan"]
                )
            except tk.TclError:
                pass
        try:
            self.root.after(0, apply)
        except tk.TclError:
            pass

    def inject_reward_overlay(self, driver, names):
        try:
            safe_names = json.dumps([daily_reward_name(day) for day in range(1, 29)], ensure_ascii=False)
            driver.execute_script("""
                const old = document.getElementById('audition-daily-login-28-overlay');
                if (old) old.remove();
                const names = %s;
                const panel = document.createElement('section');
                panel.id = 'audition-daily-login-28-overlay';
                panel.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:2147483647;background:#fff;color:#222;'
                  + 'border:2px solid #1565c0;border-radius:10px;padding:12px;width:360px;max-height:55vh;'
                  + 'overflow:auto;box-shadow:0 4px 20px #0005;font:13px/1.4 Arial,sans-serif';
                const title = document.createElement('div');
                title.textContent = 'Audition Daily Login — รายการ 28 วัน';
                title.style.cssText = 'font-weight:bold;font-size:15px;margin-bottom:8px';
                panel.appendChild(title);
                const note = document.createElement('div');
                note.textContent = 'รายชื่ออ้างอิงจากภาพ Daily Login ที่ผู้ใช้ส่งมา';
                note.style.cssText = 'color:#8a5200;margin-bottom:8px';
                panel.appendChild(note);
                for (let i=1; i<=28; i++) {
                  const row = document.createElement('div');
                  row.style.cssText = 'padding:4px 0;border-top:1px solid #ddd';
                  row.textContent = 'Day ' + i + ': ' + (names[i-1] || 'หน้าเว็บไม่เปิดเผยชื่อแยกตามวัน');
                  panel.appendChild(row);
                }
                const close = document.createElement('button');
                close.textContent = 'ปิด';
                close.style.cssText = 'margin-top:8px;padding:5px 12px;cursor:pointer';
                close.onclick = () => panel.remove();
                panel.appendChild(close);
                document.body.appendChild(panel);
            """ % safe_names)
        except Exception as e:
            self.log(f"⚠️ แสดงตารางบนหน้าเว็บไม่สำเร็จ: {str(e).splitlines()[0]}")

    def toggle_password_visibility(self):
        if self.is_pass_visible:
            self.save_settings()
            self.actual_accounts_text = self.txt_accounts.get("1.0", "end-1c")
            masked_lines = []
            lines = self.actual_accounts_text.splitlines()
            i = 0
            while i < len(lines):
                raw = lines[i]
                line = raw.strip()
                if not line:
                    masked_lines.append(raw)
                    i += 1
                    continue
                if "|" in line:
                    user, password = line.split("|", 1)
                    masked_lines.append(f"{'•' * len(user.strip())}|{'•' * len(password.strip())}")
                    i += 1
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    masked_lines.append(f"{'•' * len(parts[0])} {'•' * len(parts[1])}")
                    i += 1
                    continue
                if i + 1 < len(lines) and lines[i + 1].strip():
                    masked_lines.append('•' * len(line))
                    masked_lines.append('•' * len(lines[i + 1].strip()))
                    i += 2
                else:
                    masked_lines.append('•' * len(line))
                    i += 1

            self.txt_accounts.config(state="normal")
            self.txt_accounts.delete("1.0", tk.END)
            self.txt_accounts.insert(tk.END, "\n".join(masked_lines))
            self.txt_accounts.config(state="disabled")
            self.btn_toggle_pass.config(text="👁️ แสดง ID/รหัสผ่าน", bg="#1565c0", fg="white")
            self.is_pass_visible = False
        else:
            self.txt_accounts.config(state="normal")
            self.txt_accounts.delete("1.0", tk.END)
            self.txt_accounts.insert(tk.END, self.actual_accounts_text)
            self.btn_toggle_pass.config(text="👁️ ซ่อน ID/รหัสผ่าน", bg="#e0e0e0", fg="black")
            self.is_pass_visible = True

    def save_settings(self, event=None):
        try:
            if not self.is_pass_visible:
                account_text = self.actual_accounts_text
            else:
                account_text = self.txt_accounts.get("1.0", "end-1c")
            settings = {}
            try:
                with open(self.settings_path, "r", encoding="utf-8") as existing:
                    settings = json.load(existing)
                if not isinstance(settings, dict):
                    settings = {}
            except (OSError, ValueError):
                settings = {}
            settings["accounts_text"] = account_text
            if hasattr(self, "txt_url"):
                settings["daily_login_url"] = self.txt_url.get().strip()
            if hasattr(self, "txt_code_url"):
                settings["item_code_url"] = self.txt_code_url.get().strip()
            with open(self.settings_path, "w", encoding="utf-8") as file:
                json.dump(settings, file, ensure_ascii=False, indent=2)
        except (OSError, tk.TclError) as exc:
            print("บันทึกการตั้งค่าไม่สำเร็จ:", exc)

    def save_link_settings(self):
        daily_url = self.txt_url.get().strip()
        code_url = self.txt_code_url.get().strip()
        for label, url in (("Daily Login", daily_url), ("หน้าเติมโค้ด", code_url)):
            if url and not re.match(r"^https?://", url, re.IGNORECASE):
                messagebox.showwarning("ลิงก์ไม่ถูกต้อง", f"ลิงก์ {label} ต้องขึ้นต้นด้วย http:// หรือ https://", parent=self.root)
                return
        self.save_settings()
        self.log("💾 บันทึกลิงก์แล้ว — ปิดและเปิดโปรแกรมใหม่ก็ยังจำลิงก์นี้")
        messagebox.showinfo("บันทึกลิงก์สำเร็จ", "บันทึกลิงก์ Daily Login และหน้าเติมโค้ดแล้วค่ะ\nครั้งต่อไปที่เปิดโปรแกรม จะโหลดลิงก์ชุดนี้ให้อัตโนมัติ", parent=self.root)

    def load_settings(self):
        try:
            with open(self.settings_path, "r", encoding="utf-8") as file:
                settings = json.load(file)
            account_text = settings.get("accounts_text", "")
            if isinstance(account_text, str) and account_text:
                self.txt_accounts.delete("1.0", tk.END)
                self.txt_accounts.insert("1.0", account_text)
                self.log("💾 โหลดรายการบัญชีที่บันทึกไว้โดยอัตโนมัติ")
            daily_url = settings.get("daily_login_url")
            code_url = settings.get("item_code_url")
            if isinstance(daily_url, str) and daily_url.strip():
                self.txt_url.delete(0, tk.END)
                self.txt_url.insert(0, daily_url.strip())
            if isinstance(code_url, str) and code_url.strip():
                self.txt_code_url.delete(0, tk.END)
                self.txt_code_url.insert(0, code_url.strip())
            if daily_url or code_url:
                self.log("🔗 โหลดลิงก์ที่บันทึกไว้จากครั้งก่อนแล้ว")
        except FileNotFoundError:
            pass
        except (OSError, ValueError, tk.TclError) as exc:
            print("โหลดการตั้งค่าที่บันทึกไว้ไม่สำเร็จ:", exc)

    def load_accounts_file(self):
        file_path = filedialog.askopenfilename(
            parent=self.root,
            title="เลือกไฟล์รายการ ID / Password",
            filetypes=[("ไฟล์ข้อความ", "*.txt"), ("ทุกไฟล์", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8-sig") as file:
                content = file.read()
            if not self.is_pass_visible:
                self.txt_accounts.config(state="normal")
                self.is_pass_visible = True
                self.btn_toggle_pass.config(text="👁️ ซ่อน ID/รหัสผ่าน", bg="#e0e0e0", fg="black")
            self.txt_accounts.delete("1.0", tk.END)
            self.txt_accounts.insert(tk.END, content.rstrip() + ("\n" if content.strip() else ""))
            self.actual_accounts_text = ""
            self.save_settings()
            account_count = len(parse_accounts(content))
            self.log(f"📂 โหลดไฟล์บัญชีสำเร็จ: {file_path} ({account_count} บัญชี)")
            show_readable_alert(
                self.root, "โหลดไฟล์สำเร็จ",
                f"โหลดรายการจากไฟล์แล้ว\nตรวจพบ {account_count} บัญชี\n\nตรวจสอบข้อมูลในช่อง ID / Password ก่อนกดเริ่มรัน",
                kind="info"
            )
        except (OSError, UnicodeError) as exc:
            show_readable_alert(self.root, "โหลดไฟล์ไม่สำเร็จ", f"อ่านไฟล์ไม่ได้: {exc}", kind="error")

    def get_raw_accounts_text(self):
        if self.is_pass_visible:
            return self.txt_accounts.get("1.0", tk.END)
        else:
            return self.actual_accounts_text

    def open_history_detail(self, event=None):
        selected = self.history_tree.selection()
        if not selected:
            return
        values = self.history_tree.item(selected[0], "values")
        if not values:
            return
        win = tk.Toplevel(self.root)
        win.title("รายละเอียดประวัติ Item Code")
        win.configure(bg=self.colors["bg"])
        win.geometry("900x600")
        win.minsize(600, 400)
        body = tk.Frame(win, bg=self.colors["bg"], padx=12, pady=12)
        body.pack(fill="both", expand=True)
        labels = ("วันและเวลา", "ไอดีบัญชี", "Item Code", "สถานะ", "ไอเทม", "ข้อความจากเว็บ")
        for i, label in enumerate(labels):
            tk.Label(body, text=label, bg=self.colors["bg"], fg=self.colors["pink"],
                     font=("Segoe UI", 10, "bold")).pack(anchor="w")
            if i == len(labels) - 1:
                box = scrolledtext.ScrolledText(body, wrap="word", font=("Segoe UI", 11), height=12)
                box.pack(fill="both", expand=True, pady=(2, 8))
                box.insert("1.0", str(values[i]))
                box.configure(state="disabled")
            else:
                tk.Label(body, text=str(values[i]), bg="#ffffff", fg=self.colors["text"],
                         anchor="w", justify="left", wraplength=840, padx=6, pady=3).pack(fill="x", pady=(2, 5))
        tk.Button(body, text="ปิด", command=win.destroy, bg=self.colors["purple"], fg="#ffffff",
                  relief="flat", padx=16, pady=6).pack(anchor="e")

    def init_history_db(self):
        try:
            with sqlite3.connect(self.history_db_path, timeout=10) as con:
                con.execute("""CREATE TABLE IF NOT EXISTS item_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    account TEXT NOT NULL,
                    code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    item TEXT NOT NULL,
                    details TEXT NOT NULL
                )""")
                con.execute("""CREATE TABLE IF NOT EXISTS completed_accounts (
                    account TEXT PRIMARY KEY,
                    completed_at TEXT NOT NULL
                )""")
                con.commit()
        except Exception as exc:
            messagebox.showwarning("ประวัติย้อนหลัง", f"สร้างไฟล์ประวัติไม่สำเร็จ:\n{exc}", parent=self.root)

    def account_was_completed(self, account):
        try:
            with sqlite3.connect(self.history_db_path, timeout=10) as con:
                row = con.execute("SELECT 1 FROM completed_accounts WHERE account=?", (str(account),)).fetchone()
            return bool(row)
        except Exception:
            return False

    def mark_account_completed(self, account):
        try:
            with sqlite3.connect(self.history_db_path, timeout=10) as con:
                con.execute("INSERT OR REPLACE INTO completed_accounts(account, completed_at) VALUES (?, ?)",
                            (str(account), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                con.commit()
        except Exception as exc:
            self.log(f"⚠️ บันทึกสถานะบัญชีที่ทำครบแล้วไม่สำเร็จ: {str(exc).splitlines()[0]}")

    def confirmed_code_seen(self, account, code):
        try:
            with sqlite3.connect(self.history_db_path, timeout=10) as con:
                rows = con.execute(
                    "SELECT status FROM item_history WHERE account=? AND UPPER(code)=UPPER(?) ORDER BY id DESC LIMIT 20",
                    (str(account), str(code).strip())
                ).fetchall()
            for (status,) in rows:
                status = str(status or "")
                if status == "โค้ดถูกใช้งานแล้ว" or status.startswith("เติมเสร็จแล้วค่ะ") or status == "สำเร็จ":
                    return True, status
            return False, ""
        except Exception:
            return False, ""

    def set_progress(self, current, total, message):
        def update():
            try:
                pct = (current / total * 100) if total else 0
                self.progress_bar.configure(maximum=100, value=pct)
                self.progress_text.set(f"ความคืบหน้า {current}/{total} บัญชี ({pct:.0f}%) • {message}")
            except tk.TclError:
                pass
        try:
            self.root.after(0, update)
        except tk.TclError:
            pass

    def save_history_record(self, account, code, status, item="", details=""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with sqlite3.connect(self.history_db_path, timeout=10) as con:
                con.execute("INSERT INTO item_history(timestamp, account, code, status, item, details) VALUES (?, ?, ?, ?, ?, ?)",
                            (timestamp, str(account), str(code), str(status), str(item), re.sub(r"\s+", " ", str(details))[:1500]))
                con.commit()
        except Exception as exc:
            self.log(f"⚠️ บันทึกประวัติไม่สำเร็จ: {str(exc).splitlines()[0]}")
        try:
            self.root.after(0, self.refresh_history)
        except tk.TclError:
            pass

    def clear_history_filters(self):
        self.history_search_var.set("")
        self.history_status_filter.set("ทั้งหมด")
        self.history_date_from.set("")
        self.history_date_to.set("")
        self.refresh_history()

    def refresh_history(self):
        if not hasattr(self, "history_tree"):
            return
        try:
            query = self.history_search_var.get().strip().lower()
            status_filter = self.history_status_filter.get() if hasattr(self, "history_status_filter") else "ทั้งหมด"
            date_from = self.history_date_from.get().strip() if hasattr(self, "history_date_from") else ""
            date_to = self.history_date_to.get().strip() if hasattr(self, "history_date_to") else ""
            with sqlite3.connect(self.history_db_path, timeout=10) as con:
                rows = con.execute("SELECT id, timestamp, account, code, status, item, details FROM item_history ORDER BY id DESC LIMIT 20000").fetchall()
                summary_rows = con.execute("SELECT status, COUNT(*) FROM item_history GROUP BY status").fetchall()
            for iid in self.history_tree.get_children():
                self.history_tree.delete(iid)
            visible = 0
            for row in rows:
                values = row[1:]
                if query and query not in " ".join(str(v) for v in values).lower():
                    continue
                if status_filter != "ทั้งหมด" and status_filter not in str(row[4]):
                    continue
                date_part = str(row[1])[:10]
                if date_from and date_part < date_from:
                    continue
                if date_to and date_part > date_to:
                    continue
                self.history_tree.insert("", "end", iid=str(row[0]), values=values)
                visible += 1
            counts = {str(k): int(v) for k, v in summary_rows}
            success = sum(v for k, v in counts.items() if "สำเร็จ" in k and "ไม่สำเร็จ" not in k and "ไม่ได้" not in k and "ถูกใช้งานแล้ว" not in k)
            used = sum(v for k, v in counts.items() if "ถูกใช้งานแล้ว" in k)
            failed = sum(v for k, v in counts.items() if "ไม่สำเร็จ" in k or "ผิดพลาด" in k or "ล้มเหลว" in k)
            uncertain = sum(v for k, v in counts.items() if "ยืนยันผลไม่ได้" in k or "ไม่ทราบ" in k)
            if hasattr(self, "history_note"):
                self.history_note.configure(text=f"ประวัติ Daily Login + Item Code • ทั้งหมด {sum(counts.values())} รายการ | สำเร็จ/รับแต้ม {success + counts.get('รับแต้มแล้ว', 0)} | ใช้แล้ว {used} | ไม่สำเร็จ {failed} | ยังไม่ยืนยัน {uncertain} • แสดงตามตัวกรอง {visible} รายการ")
        except Exception as exc:
            self.log(f"⚠️ โหลดประวัติย้อนหลังไม่สำเร็จ: {str(exc).splitlines()[0]}")

    def backup_history(self):
        path = filedialog.asksaveasfilename(parent=self.root, title="สำรองฐานข้อมูลประวัติ", defaultextension=".sqlite3",
            filetypes=[("SQLite database", "*.sqlite3"), ("All files", "*.*")], initialfile="audition_history_backup.sqlite3")
        if not path:
            return
        try:
            with sqlite3.connect(self.history_db_path, timeout=10) as source, sqlite3.connect(path) as target:
                source.backup(target)
            messagebox.showinfo("สำรองสำเร็จ", f"สำรองประวัติแล้วค่ะ\n{path}", parent=self.root)
        except Exception as exc:
            messagebox.showerror("สำรองไม่สำเร็จ", str(exc), parent=self.root)

    def restore_history(self):
        path = filedialog.askopenfilename(parent=self.root, title="เลือกไฟล์สำรองประวัติ", filetypes=[("SQLite database", "*.sqlite3 *.db"), ("All files", "*.*")])
        if not path:
            return
        if os.path.abspath(path) == os.path.abspath(self.history_db_path):
            messagebox.showwarning("กู้คืนประวัติ", "ไฟล์นี้เป็นฐานข้อมูลที่กำลังใช้งานอยู่ค่ะ", parent=self.root)
            return
        if not messagebox.askyesno("ยืนยันกู้คืน", "การกู้คืนจะแทนที่ประวัติปัจจุบันทั้งหมด ต้องการดำเนินการต่อไหมคะ?\nแนะนำให้สำรองฐานข้อมูลปัจจุบันก่อน", icon="warning", parent=self.root):
            return
        try:
            with sqlite3.connect(path, timeout=10) as source:
                valid = source.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='item_history'").fetchone()
                if not valid:
                    raise ValueError("ไฟล์นี้ไม่มีตาราง item_history ที่รองรับ")
                columns = [r[1] for r in source.execute("PRAGMA table_info(item_history)").fetchall()]
                required = {"timestamp", "account", "code", "status", "item", "details"}
                if not required.issubset(set(columns)):
                    raise ValueError("โครงสร้างฐานข้อมูลไม่ตรงกับประวัติของโปรแกรมนี้")
                rows = source.execute("SELECT timestamp, account, code, status, item, details FROM item_history ORDER BY id").fetchall()
            with sqlite3.connect(self.history_db_path, timeout=10) as target:
                target.execute("DELETE FROM item_history")
                target.executemany("INSERT INTO item_history(timestamp, account, code, status, item, details) VALUES (?, ?, ?, ?, ?, ?)", rows)
                target.commit()
            self.refresh_history()
            messagebox.showinfo("กู้คืนสำเร็จ", f"กู้คืนประวัติ {len(rows)} รายการแล้วค่ะ", parent=self.root)
        except Exception as exc:
            messagebox.showerror("กู้คืนไม่สำเร็จ", str(exc), parent=self.root)

    def export_diagnostic_report(self):
        path = filedialog.asksaveasfilename(parent=self.root, title="บันทึกรายงานปัญหา", defaultextension=".txt",
            filetypes=[("Text file", "*.txt")], initialfile="audition_diagnostic_report.txt")
        if not path:
            return
        try:
            try:
                selenium_version = __import__("selenium").__version__
            except Exception:
                selenium_version = "ตรวจสอบไม่ได้"
            log_text = self.txt_log.get("1.0", tk.END) if hasattr(self, "txt_log") else "ไม่มี log"
            report = ["Audition DailyLogin diagnostic report", f"Time: {datetime.now():%Y-%m-%d %H:%M:%S}",
                f"OS: {platform.platform()}", f"Python: {sys.version}", f"Frozen EXE: {getattr(sys, 'frozen', False)}",
                f"Selenium: {selenium_version}", f"History DB exists: {os.path.exists(self.history_db_path)}",
                f"History DB path: {self.history_db_path}", "", "--- Application log ---", log_text]
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(report))
            messagebox.showinfo("สร้างรายงานแล้ว", f"บันทึกรายงานปัญหาแล้วค่ะ\n{path}\n\nรายงานนี้ไม่รวมรหัสผ่านบัญชี", parent=self.root)
        except Exception as exc:
            messagebox.showerror("สร้างรายงานไม่สำเร็จ", str(exc), parent=self.root)

    def delete_selected_history(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showinfo("ลบประวัติ", "กรุณาเลือกรายการในตารางที่ต้องการลบก่อนค่ะ", parent=self.root)
            return
        count = len(selected)
        if not messagebox.askyesno("ยืนยันการลบ", f"ต้องการลบประวัติที่เลือก {count} รายการใช่ไหม?\nการลบนี้ไม่สามารถย้อนกลับได้", icon="warning", parent=self.root):
            return
        try:
            ids = [int(iid) for iid in selected]
            with sqlite3.connect(self.history_db_path, timeout=10) as con:
                con.executemany("DELETE FROM item_history WHERE id = ?", [(rid,) for rid in ids])
                con.commit()
            self.refresh_history()
            messagebox.showinfo("ลบสำเร็จ", f"ลบประวัติ {count} รายการแล้วค่ะ", parent=self.root)
        except Exception as exc:
            messagebox.showerror("ลบไม่สำเร็จ", f"ไม่สามารถลบประวัติได้:\n{exc}", parent=self.root)

    def clear_all_history(self):
        try:
            with sqlite3.connect(self.history_db_path, timeout=10) as con:
                count = con.execute("SELECT COUNT(*) FROM item_history").fetchone()[0]
            if count == 0:
                messagebox.showinfo("ล้างประวัติ", "ไม่มีประวัติให้ลบค่ะ", parent=self.root)
                return
            if not messagebox.askyesno("ยืนยันล้างประวัติทั้งหมด", f"ต้องการลบประวัติทั้งหมด {count} รายการใช่ไหม?\nข้อมูลที่ลบแล้วกู้คืนไม่ได้", icon="warning", parent=self.root):
                return
            with sqlite3.connect(self.history_db_path, timeout=10) as con:
                con.execute("DELETE FROM item_history")
                con.commit()
            self.refresh_history()
            messagebox.showinfo("ล้างประวัติสำเร็จ", f"ล้างประวัติทั้งหมด {count} รายการแล้วค่ะ", parent=self.root)
        except Exception as exc:
            messagebox.showerror("ล้างประวัติไม่สำเร็จ", f"เกิดข้อผิดพลาด:\n{exc}", parent=self.root)

    def export_history_csv(self):
        path = filedialog.asksaveasfilename(parent=self.root, title="ส่งออกประวัติย้อนหลัง", defaultextension=".csv",
                                            filetypes=[("CSV UTF-8", "*.csv")], initialfile="audition_history.csv")
        if not path:
            return
        try:
            with sqlite3.connect(self.history_db_path, timeout=10) as con:
                rows = con.execute("SELECT timestamp, account, code, status, item, details FROM item_history ORDER BY id DESC").fetchall()
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["วันและเวลา", "ไอดีบัญชี", "Item Code", "สถานะ", "ไอเทม", "ข้อความจากเว็บ"])
                writer.writerows(rows)
            messagebox.showinfo("ส่งออกสำเร็จ", f"บันทึกประวัติ {len(rows)} รายการแล้ว\n{path}", parent=self.root)
        except Exception as exc:
            messagebox.showerror("ส่งออกไม่สำเร็จ", str(exc), parent=self.root)

    def open_history_folder(self):
        folder = os.path.dirname(self.history_db_path)
        try:
            if os.name == "nt":
                os.startfile(folder)
            elif sys.platform == "darwin":
                import subprocess; subprocess.Popen(["open", folder])
            else:
                import subprocess; subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            messagebox.showerror("เปิดโฟลเดอร์ไม่สำเร็จ", str(exc), parent=self.root)

    def log(self, msg):
        timestamp = time.strftime("[%H:%M:%S]")
        clean_msg = str(msg).replace('\n', ' ').strip()

        def append_log():
            try:
                self.txt_log.insert(tk.END, f"{timestamp} {clean_msg}\n")
                self.txt_log.see(tk.END)
            except tk.TclError:
                pass

        try:
            self.root.after(0, append_log)
        except tk.TclError:
            pass

    def classify_redeem_result(self, result_text, visible_text=""):
        raw_text = f"{result_text or ''} {visible_text or ''}".strip()
        text = raw_text.lower()
        compact = re.sub(r"\s+", " ", text)
        if re.search(r"\[\s*error\s*[-–]?\s*3\s*\]", compact) and re.search(
            r"item\s*code\s*ถูกใช้งานแล้ว|itemcode\s*ถูกใช้งานแล้ว|ถูกใช้งานแล้วค่ะ", compact
        ):
            return "โค้ดถูกใช้งานแล้ว"
        
        already_used_terms = (
            "โค้ดถูกใช้งานแล้ว", "รหัสถูกใช้งานแล้ว", "ถูกใช้งานไปแล้ว",
            "ใช้โค้ดนี้ไปแล้ว", "ใช้ไปแล้ว", "ถูกใช้แล้ว",
            "โค้ดนี้ถูกใช้แล้ว", "รหัสนี้ถูกใช้แล้ว", "โค้ดนี้ถูกใช้งานแล้ว",
            "รหัสนี้ถูกใช้งานแล้ว", "โค้ดนี้ถูกใช้ไปแล้ว", "รหัสนี้ถูกใช้ไปแล้ว",
            "มีการใช้โค้ดนี้แล้ว", "มีการใช้รหัสนี้แล้ว", "โค้ดได้ถูกใช้งานแล้ว",
            "รหัสได้ถูกใช้งานแล้ว",
            "itemcode ถูกใช้งานแล้ว", "item code ถูกใช้งานแล้ว",
            "itemcode ถูกใช้แล้ว", "item code ถูกใช้แล้ว",
            "itemcode ถูกใช้งานไปแล้ว", "item code ถูกใช้งานไปแล้ว",
            "itemcode ถูกใช้งานแล้วค่ะ", "item code ถูกใช้งานแล้วค่ะ",
            "used code", "code has already been used",
            "this code has been used", "already used", "already redeemed",
            "code has been used", "code already used", "this code was redeemed"
        )
        if any(term in text for term in already_used_terms):
            return "โค้ดถูกใช้งานแล้ว"

        failed_terms = (
            "ไม่สำเร็จ", "ไม่ถูกต้อง", "ไม่พบโค้ด",
            "หมดอายุ", "หมดเขต", "ไม่สามารถใช้", "ไม่สามารถเติม", "ผิดพลาด",
            "invalid", "expired", "failed",
            "ไม่พบ item code", "ไม่พบ itemcode"
        )
        success_terms = (
            "เติมสำเร็จ", "แลกรับสำเร็จ", "รับไอเทมสำเร็จ", "ใช้โค้ดสำเร็จ",
            "ได้รับไอเทม", "ได้รับไอเท็ม", "รับรางวัลสำเร็จ",
            "redeem successful", "successfully redeemed", "redemption successful"
        )
        if any(term in text for term in failed_terms):
            return "ไม่สำเร็จ"
        if any(term in text for term in success_terms):
            return "เติมเสร็จแล้วค่ะ (ยืนยันจากข้อความเว็บ)"
        return "ยังยืนยันผลไม่ได้"

    def get_visible_result_details(self, driver):
        chunks = []
        try:
            main_text = driver.execute_script(
                "return document.body ? document.body.innerText : '';"
            ) or ""
            if main_text.strip():
                chunks.append(main_text)
        except Exception:
            pass

        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            for frame in frames:
                try:
                    driver.switch_to.frame(frame)
                    frame_text = driver.execute_script(
                        "return document.body ? document.body.innerText : '';"
                    ) or ""
                    if frame_text.strip():
                        chunks.append(frame_text)
                except Exception:
                    pass
                finally:
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
        except Exception:
            pass

        visible = "\n".join(chunks)
        item_name = ""
        patterns = [
            r"(?:ไอเทม|ไอเท็ม|item(?:\s*name)?)\s*[:：]\s*([^\n]+)",
            r"(?:ได้รับ|รับไอเทม|รับไอเท็ม)\s*[:：]?\s*([^\n]+)",
            r"(?:reward|รางวัล)\s*[:：]\s*([^\n]+)"
        ]
        for pattern in patterns:
            match = re.search(pattern, visible, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if candidate and len(candidate) <= 160:
                    item_name = candidate
                    break
        return visible, item_name

    def extract_item_name_from_text(self, text):
        if not text:
            return ""
        patterns = [
            r"(?:ไอเทม|ไอเท็ม|item(?:\s*name)?)\s*[:：]\s*([^\n\r]+)",
            r"(?:ได้รับ|รับไอเทม|รับไอเท็ม)\s*[:：]?\s*([^\n\r]+)",
            r"(?:reward|รางวัล)\s*[:：]\s*([^\n\r]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                candidate = re.sub(r"\s+", " ", candidate)
                if candidate and len(candidate) <= 160:
                    return candidate
        return ""

    def notify_daily_claim(self, account_id, day_num, alert_text, item_name=""):
        generic_text = ("รับแต้ม", "daily login", "สำเร็จ", "success", "รับรางวัล")
        if item_name and not any(term in item_name.lower() for term in generic_text):
            shown_name = item_name
        else:
            shown_name = daily_reward_name(day_num) or "ยังไม่ทราบชื่อรางวัล"
        self.log(f"🎁 รางวัลที่รับแล้ว: Day {day_num} = {shown_name}")
        line = f"🎁 รับแต้ม Day {day_num} | ไอดี {account_id} | ได้รับไอเทม: {shown_name}"
        self.log(line)
        self.save_history_record(
            account_id,
            f"Daily Login Day {day_num}",
            "รับแต้มแล้ว",
            shown_name,
            f"Daily Login reward confirmed. Day {day_num}. Website response: {re.sub(r'\s+', ' ', str(alert_text or '')).strip()[:1200]}"
        )
        def update():
            try:
                self.notify_label.config(text="🔔 " + line, fg=self.colors["cyan"])
            except tk.TclError:
                pass
        try:
            self.root.after(0, update)
        except tk.TclError:
            pass

    def notify_redeem_result(self, account_id, code, status, item_name="", source_text=""):
        item_display = item_name if item_name else "ยังจับคู่ชื่อไอเทมกับโค้ดนี้ไม่ได้จากข้อความเว็บ"
        if status.startswith("เติมเสร็จแล้วค่ะ"):
            line = f"✅ เติมเสร็จแล้วค่ะ! | ไอดี {account_id} | โค้ด {code} | ไอเทม: {item_display}"
        else:
            line = f"🎁 ผลเติม | ไอดี {account_id} | โค้ด {code} | สถานะ: {status} | ไอเทม: {item_display}"
        self.log(line)
        site_response = re.sub(r"\s+", " ", (source_text or "")).strip()
        if site_response:
            self.log(f"🌐 ข้อความเว็บจริง: {site_response[:500]}")

        def update_banner():
            try:
                color = "#176b3a" if status.startswith("เติมเสร็จแล้วค่ะ") else (
                    "#a11232" if status in ("ไม่สำเร็จ", "โค้ดถูกใช้งานแล้ว") else "#8a4b00"
                )
                banner_text = "🔔  " + line
                if site_response:
                    banner_text += "\n🌐 ข้อความเว็บ: " + site_response[:260]
                self.notify_label.config(text=banner_text, fg=color, wraplength=1450, height=4, justify="left", anchor="w")
            except tk.TclError:
                pass

        try:
            self.root.after(0, update_banner)
        except tk.TclError:
            pass

        self.account_results.setdefault(account_id, []).append({
            "code": code, "status": status, "item": item_name or "ยังจับคู่ชื่อไอเทมกับโค้ดนี้ไม่ได้จากข้อความเว็บ",
            "source_text": (source_text or "").strip()[:500]
        })
        self.save_history_record(account_id, code, status, item_name or "ยังจับคู่ชื่อไอเทมไม่ได้", source_text or "")

    def show_final_summary(self, total_accounts):
        lines = ["สรุปผลการทำงานรายไอดี"]
        for account_id, entries in self.account_results.items():
            lines.append(f"\nไอดี {account_id}:")
            for entry in entries:
                lines.append(f"  • โค้ด: {entry['code']}\n    สถานะ: {entry['status']}\n    ไอเทม: {entry['item']}")
                if entry.get("source_text"):
                    lines.append(f"    ข้อความจากเว็บ/Log: {entry['source_text']}")
        if not self.account_results:
            lines.append("ยังไม่มีผลการเติม Item Code ที่บันทึกได้")
        summary = "\n".join(lines)
        self.log("📊 " + summary.replace("\n", " | "))

        def show():
            try:
                show_readable_alert(self.root, "สรุปผลการเติม Item Code", summary, kind="info")
            except tk.TclError:
                pass
        try:
            self.root.after(0, show)
        except tk.TclError:
            pass

    def trigger_playpark_login(self, driver):
        xpaths = [
            "//button[contains(text(), 'เข้าสู่ระบบ')]",
            "//input[@value='เข้าสู่ระบบ' or @type='submit']",
            "//a[contains(text(), 'เข้าสู่ระบบ')]",
            "//div[contains(text(), 'เข้าสู่ระบบ') and contains(@class, 'btn')]"
        ]
        for xp in xpaths:
            try:
                btn = driver.find_element(By.XPATH, xp)
                if btn.is_displayed():
                    btn.click()
                    return True
            except Exception:
                pass
        
        script = """
            var targets = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button'], a, div'));
            var loginBtn = targets.find(el => {
                var txt = (el.innerText || el.value || '').trim();
                return txt === 'เข้าสู่ระบบ' && el.offsetWidth > 0 && el.offsetHeight > 0;
            });
            if (loginBtn) { loginBtn.click(); return true; }
            return false;
        """
        return driver.execute_script(script)

    def get_checked_days_count(self, driver):
        script = """
            var checkedImgs = Array.from(document.querySelectorAll('img')).filter(img => {
                var src = (img.src || '').toLowerCase();
                var isVisible = img.offsetWidth > 0 && img.offsetHeight > 0;
                return isVisible && (src.includes('check') || src.includes('checked') || src.includes('icon_check'));
            });
            return checkedImgs.length;
        """
        try:
            return driver.execute_script(script)
        except Exception:
            return 0

    def find_and_click_reward_button(self, driver):
        xpaths = [
            "//*[contains(text(), 'รับรางวัล')]",
            "//a[contains(@onclick, 'Get') or contains(@onclick, 'Reward') or contains(@href, 'Reward')]",
            "//button[contains(text(), 'รับรางวัล')]",
            "//img[contains(@src, 'btn') or contains(@src, 'reward') or contains(@alt, 'รับรางวัล')]/.."
        ]
        for xpath in xpaths:
            elements = driver.find_elements(By.XPATH, xpath)
            visible_elements = [el for el in elements if el.is_displayed()]
            if visible_elements:
                target = visible_elements[-1]
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
                time.sleep(0.3)
                try:
                    target.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", target)
                return True
        return False

    def redeem_item_codes_for_account(self, driver, id_text, pass_text, index, total, codes_to_redeem, code_reward_names=None):
        code_url = self.txt_code_url.get().strip()
        if not code_url:
            code_url = "https://secure2.playpark.com/itemcode/AUItemCode/AuLogin.aspx"

        wait = WebDriverWait(driver, 15)
        webhook_url = self.txt_webhook.get().strip()

        for c_idx, item_code in enumerate(codes_to_redeem, 1):
            if not self.is_running:
                break

            already_done, previous_status = self.confirmed_code_seen(id_text, item_code)
            if already_done:
                self.log(f"⏭️ [{index}/{total}] ข้ามโค้ด {item_code} ของไอดี {id_text}: มีประวัติยืนยันแล้ว ({previous_status})")
                continue

            try:
                self.log(f"[{index}/{total}] 🌐 เปิดหน้าเติม Item Code เพื่อเติมโค้ด [{c_idx}/{len(codes_to_redeem)}]: {item_code}")
                driver.get(code_url)
                time.sleep(1.4)

                try:
                    self.log(f"[{index}/{total}] 1️⃣ คลิกปุ่ม PlayID LOGIN...")
                    playid_clicked = False
                    playid_xpaths = [
                        "//a[contains(text(), 'PlayID') or contains(text(), 'PLAYID')]",
                        "//button[contains(text(), 'PlayID') or contains(text(), 'PLAYID')]",
                        "//div[contains(text(), 'PlayID') or contains(text(), 'PLAYID')]",
                        "//img[contains(@src, 'playid')]/.."
                    ]
                    for xp in playid_xpaths:
                        try:
                            btn_playid = driver.find_element(By.XPATH, xp)
                            if btn_playid.is_displayed():
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_playid)
                                time.sleep(0.3)
                                try:
                                    btn_playid.click()
                                except Exception:
                                    driver.execute_script("arguments[0].click();", btn_playid)
                                playid_clicked = True
                                break
                        except Exception:
                            pass

                    if not playid_clicked:
                        driver.execute_script("""
                            var elems = Array.from(document.querySelectorAll('a, button, div, span'));
                            var target = elems.find(el => (el.innerText || '').toUpperCase().includes('PLAYID'));
                            if (target) { target.click(); }
                        """)

                    time.sleep(1.4)
                except Exception:
                    pass

                try:
                    input_user = wait.until(EC.presence_of_element_located((
                        By.XPATH, "//input[@type='text' or @name='username' or @id='username' or contains(@placeholder, 'ไอดี')]"
                    )))
                    input_pass = driver.find_element(By.XPATH, "//input[@type='password']")

                    self.log(f"[{index}/{total}] 2️⃣ กรอกไอดี {id_text} และรหัสผ่าน...")
                    input_user.clear()
                    input_user.send_keys(id_text)
                    time.sleep(0.2)

                    input_pass.clear()
                    input_pass.send_keys(pass_text)
                    time.sleep(0.2)

                    self.log(f"[{index}/{total}] 3️⃣ คลิกปุ่มสีฟ้า 'เข้าสู่ระบบ'...")
                    clicked = self.trigger_playpark_login(driver)
                    if not clicked:
                        input_pass.send_keys(Keys.ENTER)

                    time.sleep(2.0)
                except Exception:
                    pass

                self.log(f"[{index}/{total}] 4️⃣ เลือก Server, ป้อนโค้ด {item_code} และคลิก 'ตกลง'...")
                
                try:
                    driver.execute_script("""
                        var serverSelects = document.querySelectorAll('select, div[id*="server"], div[class*="select"]');
                        if (serverSelects.length > 0) {
                            var target = serverSelects[0];
                            target.click();
                            if (target.tagName === 'SELECT' && target.options.length > 1) {
                                target.selectedIndex = 1;
                                target.dispatchEvent(new Event('change'));
                            }
                        }
                    """)
                    time.sleep(0.7)
                except Exception:
                    pass

                try:
                    code_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                        By.XPATH, "//input[@type='text' or contains(@id, 'code') or contains(@id, 'ItemCode') or contains(@name, 'code') or contains(@placeholder, 'โค้ด')]"
                    )))
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", code_input)
                    code_input.clear()
                    code_input.send_keys(item_code)
                    time.sleep(0.7)
                except Exception:
                    pass

                res_text = "ยังยืนยันผลไม่ได้"
                try:
                    time.sleep(0.7)

                    try:
                        alert = driver.switch_to.alert
                        res_text = alert.text or "พบหน้าต่างยืนยัน"
                        alert.accept()
                        self.log(f"[{index}/{total}] ยืนยันหน้าต่างแจ้งเตือนแล้ว: {res_text}")
                    except Exception:
                        ok_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((
                                By.XPATH,
                                "//*[self::button or self::input[@type='button' or @type='submit'] or self::a]"
                                "[normalize-space(.)='ตกลง' or normalize-space(@value)='ตกลง']"
                            ))
                        )
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                            ok_button
                        )
                        time.sleep(0.2)
                        ok_button.click()
                        time.sleep(3.0) 
                        res_text = "คลิกปุ่มตกลงแล้ว; กำลังตรวจผล"

                    try:
                        WebDriverWait(driver, 5).until(EC.alert_is_present())
                        alert = driver.switch_to.alert
                        alert_text = alert.text
                        alert.accept()
                        if alert_text:
                            res_text = alert_text
                    except TimeoutException:
                        pass

                    time.sleep(1.0)
                except TimeoutException:
                    res_text = "ไม่พบปุ่มตกลงที่กดได้ภายในเวลาที่กำหนด"
                    self.log(f"⚠️ [{index}/{total}] {res_text}; ตรวจชื่อปุ่ม/หน้าต่างยืนยันในหน้าเว็บ")
                except Exception as e:
                    res_text = f"กดตกลงไม่สำเร็จ: {str(e).splitlines()[0]}"
                    self.log(f"⚠️ [{index}/{total}] {res_text}")

                visible_result_text, detected_item_name = self.get_visible_result_details(driver)
                
                if not visible_result_text.strip():
                    time.sleep(2.0)
                    visible_result_text, detected_item_name = self.get_visible_result_details(driver)

                combined_result_text = f"{res_text or ''} {visible_result_text or ''}".strip()
                if combined_result_text:
                    self.log(f"🔎 [{index}/{total}] ข้อความผลลัพธ์ที่ตรวจพบ: {combined_result_text[:700]}")
                if not detected_item_name:
                    detected_item_name = get_item_name_for_code(item_code)
                if not detected_item_name and code_reward_names:
                    detected_item_name = code_reward_names.get(item_code.strip().upper(), "")
                if detected_item_name:
                    self.log(f"🎁 [{index}/{total}] โค้ด {item_code} → ไอเทม: {detected_item_name}")
                else:
                    self.log(f"ℹ️ [{index}/{total}] โค้ด {item_code}: ยังจับคู่ชื่อไอเทมไม่ได้")
                redeem_status = self.classify_redeem_result(res_text, visible_result_text)
                self.notify_redeem_result(id_text, item_code, redeem_status, detected_item_name, combined_result_text)

                if webhook_url:
                    send_discord_webhook(
                        webhook_url,
                        f"🎁 **[Audition เติม Item Code]**\n👤 **ไอดี:** `{id_text}`\n🔑 **โค้ด:** `{item_code}`\n📦 **ไอเทม:** `{detected_item_name or 'เว็บไม่ได้ระบุชื่อไอเทม'}`\n✨ **ผลลัพธ์:** `{res_text}`"
                    )

                try:
                    driver.execute_script("""
                        var links = Array.from(document.querySelectorAll('a, button, div'));
                        var logoutBtn = links.find(el => {
                            var t = (el.innerText || '').trim();
                            return (t.includes('ออกจากระบบ') || t.includes('กลับสู่หน้า Login') || t.includes('Logout')) && el.offsetParent !== null;
                        });
                        if (logoutBtn) { logoutBtn.click(); }
                    """)
                    time.sleep(1.4)
                except Exception:
                    pass

            except Exception as e:
                self.log(f"⚠️ ข้ามโค้ด {item_code} เนื่องจากเกิดข้อผิดพลาด: {str(e).splitlines()[0]}")

    def inspect_login_state(self, driver):
        """ตรวจสอบสถานะหลังล็อกอิน อ้างอิงข้อความแจ้งเตือนจริงจากหน้าเว็บ PlayPark"""
        try:
            body_text = (driver.execute_script(
                "return document.body ? document.body.innerText : '';"
            ) or "")
        except Exception:
            body_text = ""

        # 1. ดักจับข้อความป้องกันความปลอดภัย/CAPTCHA
        challenge_terms = (
            "captcha", "verify that you are human", "unusual traffic",
            "ยืนยันตัวตน", "ตรวจสอบความปลอดภัย", "ยืนยันว่าคุณเป็นมนุษย์",
            "ลองอีกครั้งภายหลัง", "too many attempts", "account verification"
        )
        if any(term in body_text.lower() for term in challenge_terms):
            return "security_check", "พบข้อความ CAPTCHA / ป้องกันความปลอดภัยของเว็บ"

        # 2. ดักจับข้อความ Error รหัสผ่านไม่ถูกต้องโดยตรงจากหน้าเว็บ PlayPark
        error_terms = (
            "ขออภัย, รหัสผ่านไม่ถูกต้อง!",
            "ขออภัย, รหัสผ่านไม่ถูกต้อง",
            "รหัสผ่านไม่ถูกต้อง",
            "ไอดีหรือรหัสผ่านไม่ถูกต้อง",
            "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
            "invalid password",
            "incorrect password",
            "login failed",
            "เข้าสู่ระบบไม่สำเร็จ"
        )
        if any(term in body_text for term in error_terms):
            return "login_failed", "ขออภัย, รหัสผ่านไม่ถูกต้อง!"

        # 3. ถ้ายังเห็นช่องใส่รหัสผ่านอยู่แสดงว่าล็อกอินไม่ผ่าน
        try:
            visible_password_fields = [
                el for el in driver.find_elements(By.XPATH, "//input[@type='password']")
                if el.is_displayed()
            ]
        except Exception:
            visible_password_fields = []
        if visible_password_fields:
            return "login_failed", "ขออภัย, รหัสผ่านไม่ถูกต้อง!"

        return "ok", "ไม่พบสัญญาณว่าการเข้าสู่ระบบถูกปฏิเสธ"

    def process_account(self, driver, id_text, pass_text, index, total):
        wait = WebDriverWait(driver, 15)
        extracted_codes = []

        if self.do_daily_login.get():
            try:
                event_url = self.txt_url.get().strip()
                if not event_url:
                    event_url = "https://audition.playpark.com/th-th/news/daily-login-october-2026/"

                self.log(f"[{index}/{total}] 🌐 เปิดหน้าข่าว Daily Login...")
                driver.get(event_url)
                time.sleep(1.4)
                reward_names = extract_daily_reward_labels(driver)
                self.update_reward_table(reward_names)
                self.inject_reward_overlay(driver, reward_names)

                btn_green_claim = wait.until(EC.element_to_be_clickable((
                    By.XPATH, "//a[contains(@href, 'DailyLoginCenter') or contains(text(), 'รับรางวัล')] | //img[contains(@src, 'btn_get') or contains(@src, 'claim')]/.."
                )))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_green_claim)
                time.sleep(0.3)
                btn_green_claim.click()

                time.sleep(1.4)
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])

                self.log(f"[{index}/{total}] 🖱️ คลิกปุ่ม PLAYID LOGIN...")
                btn_playid = wait.until(EC.element_to_be_clickable((
                    By.XPATH, "//a[contains(text(), 'PLAYID LOGIN') or contains(text(), 'PLAYID')]"
                )))
                driver.execute_script("arguments[0].click();", btn_playid)

                self.log(f"[{index}/{total}] 🔑 กรอกไอดี {id_text} เข้าสู่ระบบ Daily Login...")
                input_user = wait.until(EC.presence_of_element_located((
                    By.XPATH, "//input[@type='text' or @name='username' or @id='username' or contains(@placeholder, 'ไอดี')]"
                )))
                input_pass = driver.find_element(By.XPATH, "//input[@type='password']")

                input_user.clear()
                input_user.send_keys(id_text)
                time.sleep(0.2)

                input_pass.clear()
                input_pass.send_keys(pass_text)
                time.sleep(0.2)

                clicked = self.trigger_playpark_login(driver)
                if not clicked:
                    input_pass.send_keys(Keys.ENTER)

                self.log(f"[{index}/{total}] ⏳ รอโหลดหน้ากระดานกิจกรรม...")
                time.sleep(2.0)

                login_state, login_detail = self.inspect_login_state(driver)
                if login_state == "security_check":
                    self.log(f"🛑 [{index}/{total}] ไอดี {id_text}: {login_detail}; หยุดชุดงานไว้ก่อนเพื่อให้ตรวจสอบด้วยตนเอง ไม่ข้ามระบบป้องกัน")
                    self.is_running = False
                    return False
                if login_state == "login_failed":
                    self.log(f"❌ [{index}/{total}] ไอดี {id_text}: {login_detail}")
                    return False

                WebDriverWait(driver, 20).until(
                    lambda d: "secure2" in d.current_url and d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(1.4)

                self.log(f"[{index}/{total}] 🎁 เริ่มกดปุ่มรับรางวัลแต้มประจำวัน...")
                initial_checked = self.get_checked_days_count(driver)
                claim_count = 0

                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.7)

                while self.is_running:
                    current_day_num = min(initial_checked + claim_count + 1, 28)

                    clicked = self.find_and_click_reward_button(driver)
                    if not clicked:
                        break

                    try:
                        WebDriverWait(driver, 4).until(EC.alert_is_present())
                        alert1 = driver.switch_to.alert
                        alert1.accept()
                    except TimeoutException:
                        break

                    time.sleep(0.7)

                    try:
                        WebDriverWait(driver, 4).until(EC.alert_is_present())
                        alert2 = driver.switch_to.alert
                        res_text = alert2.text
                        alert2.accept()
                        alert_item_name = self.extract_item_name_from_text(res_text)
                        if not alert_item_name:
                            _, visible_item_name = self.get_visible_result_details(driver)
                            alert_item_name = visible_item_name
                        if "ไม่พอ" in res_text or "หมด" in res_text or "ไม่เพียงพอ" in res_text:
                            self.log(f"[{index}/{total}] 🟢 คะแนนไม่พอแล้ว / เช็กอินครบเรียบร้อย ({res_text})")
                            break
                        else:
                            self.notify_daily_claim(id_text, current_day_num, res_text, alert_item_name)
                            claim_count += 1
                    except TimeoutException:
                        break

                    time.sleep(1.0)

                self.log(f"[{index}/{total}] 🔍 เปิดตารางประวัติกิจกรรมเพื่ออ่าน Item Code ของไอดี {id_text}...")
                extracted_codes = self.navigate_and_extract_codes(driver)
                if extracted_codes:
                    self.log(f"🎉 [{index}/{total}] อ่าน Item Code สำเร็จ {len(extracted_codes)} โค้ด: {', '.join(extracted_codes)}")
                    try:
                        with sqlite3.connect(self.history_db_path, timeout=10) as con:
                            for discovered_code in extracted_codes:
                                exists = con.execute(
                                    "SELECT 1 FROM item_history WHERE account=? AND UPPER(code)=UPPER(?) AND status='พบโค้ดจากเว็บ' LIMIT 1",
                                    (str(id_text), str(discovered_code))
                                ).fetchone()
                                if not exists:
                                    con.execute(
                                        "INSERT INTO item_history(timestamp, account, code, status, item, details) VALUES (?, ?, ?, ?, ?, ?)",
                                        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(id_text), str(discovered_code),
                                         "พบโค้ดจากเว็บ", "รอผลการเติม", "อ่านพบจากตารางประวัติกิจกรรมบนเว็บไซต์; ยังไม่ใช่ผลยืนยันการเติม")
                                    )
                            con.commit()
                        self.root.after(0, self.refresh_history)
                    except Exception as hist_exc:
                        self.log(f"⚠️ บันทึกโค้ดที่อ่านพบลงประวัติไม่สำเร็จ: {str(hist_exc).splitlines()[0]}")
                else:
                    self.log(f"⚠️ [{index}/{total}] ไม่พบ Item Code ในตารางประวัติของไอดีนี้")

                while len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except Exception as e:
                err_msg = str(e).splitlines()[0] if str(e).splitlines() else type(e).__name__
                self.log(f"⚠️ [{index}/{total}] ไอดี {id_text}: Daily Login ทำไม่ครบ ต้องตรวจสอบก่อนดำเนินการต่อ ({err_msg})")
                if self.do_daily_login.get():
                    return False

        if self.do_redeem_code.get() and self.is_running:
            try:
                codes_from_gui = [c.strip() for c in self.txt_item_codes.get("1.0", tk.END).splitlines() if c.strip() and is_valid_item_code(c.strip())]
                all_codes_to_redeem = list(dict.fromkeys(extracted_codes + codes_from_gui))
                code_reward_names = {}
                for row_num, code in enumerate(extracted_codes, start=1):
                    reward_name = daily_reward_name(row_num)
                    if reward_name:
                        code_reward_names[code.strip().upper()] = reward_name

                if self.only_permanent_items.get():
                    permanent_codes = []
                    skipped_unknown = []
                    for code in all_codes_to_redeem:
                        reward_name = code_reward_names.get(code.strip().upper(), "")
                        if not reward_name:
                            skipped_unknown.append(code)
                        elif "ถาวร" in reward_name:
                            permanent_codes.append(code)
                    all_codes_to_redeem = permanent_codes
                    if skipped_unknown:
                        self.log(
                            f"ℹ️ [{index}/{total}] โหมดถาวร: ข้าม {len(skipped_unknown)} โค้ดที่ไม่สามารถยืนยันชื่อ/ระยะเวลารางวัลได้"
                        )
                    self.log(
                        f"🔒 [{index}/{total}] เปิดโหมดเติมเฉพาะถาวร: พบโค้ดรางวัลถาวร {len(all_codes_to_redeem)} โค้ด "
                        f"(รางวัลถาวรตามตาราง: Day 7, 14, 21, 28)"
                    )

                if not all_codes_to_redeem:
                    self.log(f"⚠️ [{index}/{total}] ไอดี {id_text}: ไม่มี Item Code สำหรับนำไปเติม")
                else:
                    self.log(f"🚀 [{index}/{total}] กำลังนำ Item Code ทั้งหมด {len(all_codes_to_redeem)} โค้ดไปเติมเข้าไอดี {id_text}...")
                    self.redeem_item_codes_for_account(driver, id_text, pass_text, index, total, all_codes_to_redeem, code_reward_names)
            except Exception as e:
                self.log(f"⚠️ เกิดข้อผิดพลาดในการเติมโค้ด: {str(e).splitlines()[0]}")

        self.log(f"✅ เสร็จสิ้นทำรายการไอดี {id_text}")
        return True

    def start_process(self):
        if not self.do_daily_login.get() and not self.do_redeem_code.get():
            self.log("⚠️ กรุณาติ๊กเลือกอย่างน้อย 1 ฟังก์ชัน")
            return

        accounts = parse_accounts(self.get_raw_accounts_text())
        completed = [acc_id for acc_id, _ in accounts if self.account_was_completed(acc_id)]
        self.resume_completed_accounts = set()
        if completed:
            resume = messagebox.askyesno(
                "ทำงานต่อจากเดิมไหมคะ?",
                f"พบ {len(completed)} บัญชีที่เคยทำครบแล้วในประวัติ\n\n"
                "กด Yes เพื่อข้ามบัญชีที่ทำครบแล้วและทำต่อ\n"
                "กด No เพื่อเริ่มตรวจทุกบัญชีใหม่ (โค้ดที่ยืนยันแล้วจะยังถูกข้าม)",
                parent=self.root
            )
            if resume:
                self.resume_completed_accounts = set(completed)
        self.is_running = True
        self.account_results = {}
        self.progress_bar.configure(value=0)
        self.progress_text.set("กำลังเตรียมงาน...")
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        threading.Thread(target=self.run_loop, daemon=True).start()

    def stop_process(self):
        self.is_running = False
        def update_buttons():
            try:
                self.btn_start.config(state="normal")
                self.btn_stop.config(state="disabled")
            except tk.TclError:
                pass
        try:
            self.root.after(0, update_buttons)
        except tk.TclError:
            pass
        self.log("⏹️ หยุดการทำงาน")

    def run_loop(self):
        accounts = parse_accounts(self.get_raw_accounts_text())
        if not accounts:
            self.log("❌ ไม่พบรายการไอดี")
            self.stop_process()
            return

        self.log(f"▶️ เริ่มงาน: พบ {len(accounts)} บัญชี")
        self.log("🔎 ตรวจสอบสภาพแวดล้อมสำหรับเปิด Chrome...")
        self.log(f"ℹ️ Python/EXE path: {os.path.abspath(os.sys.executable)}")
        self.log(f"ℹ️ Selenium version: {getattr(__import__('selenium'), '__version__', 'unknown')}")
        self.log("⏳ กำลังเตรียม ChromeDriver และเปิด Chrome...")

        os.environ.setdefault("SE_MANAGER_TIMEOUT", "20")
        log_path = os.path.join(os.path.dirname(os.path.abspath(os.sys.executable)), "audition_startup.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting WebDriver; executable={os.sys.executable}; frozen={getattr(os.sys, 'frozen', False)}\n")
        except OSError:
            log_path = os.path.join(os.path.expanduser("~"), "audition_startup.log")

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-notifications")
        options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
        })
        if self.run_headless.get():
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1365,900")
        else:
            options.add_argument("--start-maximized")

        try:
            self.log("🔧 ขั้นตอน 1/3: เรียก Selenium Manager เพื่อหา Chrome/ChromeDriver...")
            started_at = time.monotonic()
            driver = webdriver.Chrome(options=options)
            elapsed = time.monotonic() - started_at
            self.log(f"✅ ขั้นตอน 2/3: เปิด WebDriver สำเร็จ ({elapsed:.1f} วินาที)")
            try:
                driver.set_page_load_timeout(45)
            except Exception:
                pass
            self.log("🌐 ขั้นตอน 3/3: เปิด Chrome สำเร็จ กำลังเริ่มตรวจบัญชี...")
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WebDriver started in {elapsed:.1f}s\n")
            except OSError:
                pass
        except Exception as e:
            err = str(e).strip() or repr(e)
            self.log(f"❌ เปิด Chrome ไม่สำเร็จ ({type(e).__name__}): {err.splitlines()[0]}")
            self.log("💡 ตรวจ Chrome ที่ติดตั้ง, อินเทอร์เน็ต/Proxy และการแพ็ก Selenium Manager ใน EXE")
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WebDriver ERROR {type(e).__name__}: {err}\n")
            except OSError:
                pass
            self.root.after(0, lambda msg=err, typ=type(e).__name__: show_readable_alert(
                self.root, "เปิด Chrome ไม่สำเร็จ", f"{typ}: {msg}\n\nLog เพิ่มเติม: {log_path}", kind="error"
            ))
            self.stop_process()
            return

        total = len(accounts)
        completed_count = 0
        for i, (acc_id, acc_pass) in enumerate(accounts, 1):
            if not self.is_running:
                break
            if acc_id in self.resume_completed_accounts:
                self.log(f"⏭️ [{i}/{total}] ข้าม {acc_id}: บัญชีนี้ทำครบแล้วจากรอบก่อน")
                completed_count += 1
                self.set_progress(i, total, f"ข้ามบัญชีที่เสร็จแล้ว: {acc_id}")
                continue
            self.set_progress(i - 1, total, f"กำลังทำบัญชี {acc_id}")
            self.log(f"👤 [{i}/{total}] เริ่มตรวจบัญชี {acc_id}...")
            account_ok = False
            try:
                account_ok = bool(self.process_account(driver, acc_id, acc_pass, i, total)) and self.is_running
            except Exception as e:
                err_msg = str(e).split('\n')[0]
                self.log(f"❌ ไอดี {acc_id} เกิดข้อผิดพลาดรุนแรง: {err_msg}")
            if account_ok:
                self.mark_account_completed(acc_id)
                completed_count += 1
            self.set_progress(i, total, f"เสร็จ/ข้าม {completed_count} จาก {total} • ล่าสุด {acc_id}")
            time.sleep(1.4)

        try:
            driver.quit()
        except Exception:
            pass

        finished_all = self.is_running
        if finished_all:
            self.log("🎉 ทำรายการครบทุกไอดีเรียบร้อยแล้ว!")
            self.set_progress(total, total, "ทำงานครบแล้ว")
            def completion_notice():
                try:
                    self.root.bell()
                    messagebox.showinfo("AUDITION SWEET DREAMS", "ทำรายการครบทุกบัญชีแล้วค่ะ 💗\nตรวจสอบสรุปผลในหน้าต่างโปรแกรมได้เลย", parent=self.root)
                except tk.TclError:
                    pass
            try:
                self.root.after(0, completion_notice)
            except tk.TclError:
                pass
        else:
            self.log("⏸️ งานหยุดก่อนครบทุกไอดีหรือถูกสั่งหยุด; สามารถเริ่มใหม่และเลือกทำต่อจากบัญชีที่เสร็จแล้วได้")
            self.set_progress(completed_count, total, "หยุดก่อนครบงาน")
        self.show_final_summary(total)
        self.stop_process()

if __name__ == "__main__":
    root = tk.Tk()
    app = AuditionDailyLoginBot(root)
    root.mainloop()