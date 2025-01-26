import sys
import os
import json
import time
import threading
import schedule
from datetime import datetime, timedelta
import win32con
import win32api
import win32security
import pystray
from PIL import Image, ImageDraw
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import darkdetect
import winreg
import logging
import shutil
from pathlib import Path
import keyboard
import requests
import psutil
from win32gui import GetForegroundWindow, GetWindowText
import hashlib
import base64
import webbrowser

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
APP_NAME = "网站访问管理"
STARTUP_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
BACKUP_DIR = "backups"
LOG_DIR = "logs"
CLOUD_BACKUP_URL = "https://api.example.com/backup"  # 替换为实际的云端备份API
DEFAULT_SHORTCUTS = {
    "toggle_block": "ctrl+shift+b",    # 开关屏蔽
    "focus_mode": "ctrl+shift+f",      # 专注模式
    "quick_unlock": "ctrl+shift+u",    # 快速解锁
    "show_stats": "ctrl+shift+s",      # 显示统计
    "add_website": "ctrl+shift+a"      # 添加网站
}

# 预设网站分类
PRESET_WEBSITES = {
    "社交媒体": [
        "facebook.com", "twitter.com", "instagram.com",
        "tiktok.com", "weibo.com", "zhihu.com",
        "linkedin.com", "pinterest.com"
    ],
    "视频娱乐": [
        "youtube.com", "netflix.com", "bilibili.com",
        "douyu.com", "huya.com", "iqiyi.com",
        "youku.com", "twitch.tv"
    ],
    "游戏平台": [
        "steam.com", "epicgames.com", "origin.com",
        "blizzard.com", "ubisoft.com", "ea.com",
        "battlenet.com", "gog.com", "4399.com"
    ],
    "购物网站": [
        "taobao.com", "jd.com", "amazon.com",
        "tmall.com", "pinduoduo.com", "ebay.com",
        "aliexpress.com", "walmart.com"
    ],
    "新闻资讯": [
        "news.qq.com", "sina.com.cn", "163.com",
        "sohu.com", "ifeng.com", "thepaper.cn",
        "cnn.com", "bbc.com"
    ],
    "在线聊天": [
        "wx.qq.com", "web.telegram.org", "discord.com",
        "messenger.com", "slack.com", "teams.microsoft.com",
        "meet.google.com", "zoom.us"
    ]
}

# 应用程序黑名单
DEFAULT_APP_BLACKLIST = {
    "游戏": [
        "steam.exe", "epicgameslauncher.exe", "battle.net.exe",
        "league of legends.exe", "genshin impact.exe"
    ],
    "社交": [
        "wechat.exe", "qq.exe", "telegram.exe",
        "discord.exe", "slack.exe"
    ],
    "娱乐": [
        "cloudmusic.exe", "potplayer.exe", "vlc.exe",
        "spotify.exe", "thunder.exe"
    ]
}

# 专注模式预设
FOCUS_MODE_PRESETS = {
    "工作模式": {
        "duration": 45,  # 分钟
        "break_time": 5,  # 分钟
        "block_social": True,
        "block_entertainment": True,
        "block_shopping": True,
        "block_apps": True
    },
    "学习模式": {
        "duration": 25,
        "break_time": 5,
        "block_social": True,
        "block_entertainment": True,
        "block_shopping": True,
        "block_apps": True
    },
    "轻度专注": {
        "duration": 30,
        "break_time": 10,
        "block_social": True,
        "block_entertainment": False,
        "block_shopping": False,
        "block_apps": False
    }
}

# 设置主题色
THEME_COLORS = {
    "primary": "#0066CC",
    "primary_hover": "#0052A3",
    "secondary": "#2D2D2D",
    "background": "#1E1E1E",
    "surface": "#2D2D2D",
    "error": "#CC3333",
    "success": "#00CC66",
    "warning": "#CC6600",
    "text": "#FFFFFF",
    "text_secondary": "#CCCCCC",
    "border": "#333333"
}

# 配置日志记录
def setup_logging():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        
    log_file = os.path.join(LOG_DIR, f"blocker_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

class BackupManager:
    def __init__(self):
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            
    def create_backup(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"config_backup_{timestamp}.json")
            
            if os.path.exists("blocker_config.json"):
                shutil.copy2("blocker_config.json", backup_file)
                logging.info(f"配置已备份到: {backup_file}")
                return True, backup_file
            return False, "配置文件不存在"
        except Exception as e:
            logging.error(f"备份失败: {str(e)}")
            return False, str(e)
            
    def restore_backup(self, backup_file):
        try:
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, "blocker_config.json")
                logging.info(f"配置已从备份还原: {backup_file}")
                return True, "配置还原成功"
            return False, "备份文件不存在"
        except Exception as e:
            logging.error(f"还原失败: {str(e)}")
            return False, str(e)
            
    def list_backups(self):
        try:
            backups = []
            for file in os.listdir(BACKUP_DIR):
                if file.startswith("config_backup_") and file.endswith(".json"):
                    path = os.path.join(BACKUP_DIR, file)
                    timestamp = os.path.getmtime(path)
                    backups.append({
                        "file": file,
                        "path": path,
                        "time": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    })
            return sorted(backups, key=lambda x: x["time"], reverse=True)
        except Exception as e:
            logging.error(f"获取备份列表失败: {str(e)}")
            return []
            
class BackupWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.backup_manager = BackupManager()
        
        # 基本设置
        self.title("备份管理")
        self.geometry("800x600")
        self.minsize(800, 600)
        
        # 设置主题
        self.configure(fg_color="#1E1E1E")
        
        # 标题
        title = ctk.CTkLabel(
            self,
            text="备份管理",
            font=("Microsoft YaHei UI", 24, "bold"),
            text_color="#FFFFFF"
        )
        title.pack(pady=20)
        
        # 主容器
        main_frame = ctk.CTkFrame(
            self,
            fg_color="#2D2D2D",
            corner_radius=20,
            border_width=1,
            border_color="#333333"
        )
        main_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        
        # 操作区域
        action_frame = ctk.CTkFrame(
            main_frame,
            fg_color="#1E1E1E",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        action_frame.pack(fill="x", padx=20, pady=15)
        
        # 创建备份按钮
        create_btn = ctk.CTkButton(
            action_frame,
            text="创建备份",
            command=self._create_backup,
            width=250,
            height=40,
            font=("Microsoft YaHei UI", 14),
            fg_color="#0066CC",
            hover_color="#0052A3",
            corner_radius=8
        )
        create_btn.pack(pady=15)
        
        # 备份列表区域
        list_frame = ctk.CTkFrame(
            main_frame,
            fg_color="#1E1E1E",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        list_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        # 列表标题
        list_title = ctk.CTkLabel(
            list_frame,
            text="备份列表",
            font=("Microsoft YaHei UI", 16, "bold"),
            text_color="#FFFFFF"
        )
        list_title.pack(pady=10)
        
        # 备份列表容器
        list_container = ctk.CTkFrame(
            list_frame,
            fg_color="#1E1E1E",
            corner_radius=8,
            border_width=1,
            border_color="#333333"
        )
        list_container.pack(fill="both", expand=True, padx=15, pady=10)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")
        
        # 备份列表
        self.backup_list = tk.Listbox(
            list_container,
            yscrollcommand=scrollbar.set,
            selectmode="single",
            font=("Microsoft YaHei UI", 12),
            bg="#1E1E1E",
            fg="#FFFFFF",
            selectbackground="#0066CC",
            selectforeground="#FFFFFF",
            borderwidth=0,
            highlightthickness=0,
            activestyle="none"
        )
        self.backup_list.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        
        # 配置滚动条
        scrollbar.config(command=self.backup_list.yview)
        
        # 还原按钮
        restore_btn = ctk.CTkButton(
            list_frame,
            text="还原选中的备份",
            command=self._restore_backup,
            width=250,
            height=40,
            font=("Microsoft YaHei UI", 14),
            fg_color="#0066CC",
            hover_color="#0052A3",
            corner_radius=8
        )
        restore_btn.pack(pady=15)
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=("Microsoft YaHei UI", 12),
            text_color="#888888"
        )
        self.status_label.pack(pady=10)
        
        # 更新备份列表
        self._update_backup_list()
        
        # 使窗口模态
        self.transient(parent)
        self.grab_set()
        
    def _create_backup(self):
        success, result = self.backup_manager.create_backup()
        if success:
            self.status_label.configure(text="备份创建成功")
            self._update_backup_list()
        else:
            self.status_label.configure(text=f"备份创建失败: {result}")
            
    def _restore_backup(self):
        selection = self.backup_list.curselection()
        if selection:
            index = selection[0]
            backup = self.backups[index]
            success, message = self.backup_manager.restore_backup(backup["path"])
            if success:
                self.status_label.configure(text="配置还原成功")
                self.parent._load_config()
            else:
                self.status_label.configure(text=f"配置还原失败: {message}")
        else:
            self.status_label.configure(text="请选择要还原的备份")
            
    def _update_backup_list(self):
        self.backup_list.delete(0, tk.END)
        self.backups = self.backup_manager.list_backups()
        for backup in self.backups:
            self.backup_list.insert(tk.END, f"📁 {backup['time']} - {backup['file']}")

class PasswordManager:
    def __init__(self):
        self.password_file = "password.json"
        self.load_password()
        
    def load_password(self):
        try:
            if os.path.exists(self.password_file):
                with open(self.password_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.has_password = True
                    self.password_hash = data.get("password_hash", "")
            else:
                self.has_password = False
                self.password_hash = ""
        except:
            self.has_password = False
            self.password_hash = ""
            
    def save_password(self, password):
        try:
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            with open(self.password_file, "w", encoding="utf-8") as f:
                json.dump({"password_hash": password_hash}, f)
            self.has_password = True
            self.password_hash = password_hash
            return True
        except:
            return False
            
    def verify_password(self, password):
        if not self.has_password:
            return True
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest() == self.password_hash
        
    def remove_password(self):
        try:
            if os.path.exists(self.password_file):
                os.remove(self.password_file)
            self.has_password = False
            self.password_hash = ""
            return True
        except:
            return False

class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent, password_manager, action="verify", callback=None):
        super().__init__(parent)
        
        self.password_manager = password_manager
        self.action = action
        self.callback = callback
        
        # 基本设置
        self.title("密码验证" if action == "verify" else "设置密码")
        self.geometry("500x400")
        self.minsize(500, 400)
        
        # 设置主题
        self.configure(fg_color="#1E1E1E")
        
        # 标题
        title = ctk.CTkLabel(
            self,
            text="请输入密码" if action == "verify" else "设置新密码",
            font=("Microsoft YaHei UI", 24, "bold"),
            text_color="#FFFFFF"
        )
        title.pack(pady=20)
        
        # 主容器
        main_frame = ctk.CTkFrame(
            self,
            fg_color="#2D2D2D",
            corner_radius=20,
            border_width=1,
            border_color="#333333"
        )
        main_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        
        # 密码输入区域
        password_frame = ctk.CTkFrame(
            main_frame,
            fg_color="#1E1E1E",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        password_frame.pack(fill="x", padx=20, pady=20)
        
        # 密码输入框
        self.password_entry = ctk.CTkEntry(
            password_frame,
            placeholder_text="输入密码...",
            width=300,
            height=40,
            font=("Microsoft YaHei UI", 14),
            fg_color="#3D3D3D",
            border_color="#4D4D4D",
            placeholder_text_color="#666666",
            show="●"
        )
        self.password_entry.pack(pady=15)
        
        # 确认密码输入框(仅在设置密码时显示)
        if action == "set":
            self.confirm_entry = ctk.CTkEntry(
                password_frame,
                placeholder_text="确认密码...",
                width=300,
                height=40,
                font=("Microsoft YaHei UI", 14),
                fg_color="#3D3D3D",
                border_color="#4D4D4D",
                placeholder_text_color="#666666",
                show="●"
            )
            self.confirm_entry.pack(pady=15)
        
        # 确定按钮
        confirm_btn = ctk.CTkButton(
            main_frame,
            text="确定",
            command=self._on_confirm,
            width=250,
            height=40,
            font=("Microsoft YaHei UI", 14),
            fg_color="#0066CC",
            hover_color="#0052A3",
            corner_radius=8
        )
        confirm_btn.pack(pady=20)
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=("Microsoft YaHei UI", 12),
            text_color="#888888"
        )
        self.status_label.pack(pady=10)
        
        # 使窗口模态
        self.transient(parent)
        self.grab_set()
        
        # 绑定回车键
        self.bind("<Return>", lambda e: self._on_confirm())
        
    def _on_confirm(self):
        if self.action == "verify":
            password = self.password_entry.get()
            if self.password_manager.verify_password(password):
                self.destroy()
                if self.callback:
                    self.callback(True)
            else:
                self.status_label.configure(text="密码错误")
                if self.callback:
                    self.callback(False)
        else:
            password = self.password_entry.get()
            confirm = self.confirm_entry.get()
            
            if not password:
                self.status_label.configure(text="请输入密码")
                return
                
            if password != confirm:
                self.status_label.configure(text="两次输入的密码不一致")
                return
                
            if self.password_manager.save_password(password):
                self.destroy()
                if self.callback:
                    self.callback(True)
            else:
                self.status_label.configure(text="密码设置失败")
                if self.callback:
                    self.callback(False)

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        # 保存父窗口引用
        self.parent = parent
        
        # 密码管理器
        self.password_manager = parent.password_manager
        
        # 基本设置
        self.title("设置")
        self.geometry("600x800")
        self.minsize(600, 800)
        
        # 设置主题
        self.configure(fg_color="#1E1E1E")
        
        # 标题
        title = ctk.CTkLabel(
            self,
            text="设置",
            font=("Microsoft YaHei UI", 24, "bold"),
            text_color="#FFFFFF"
        )
        title.pack(pady=20)
        
        # 设置容器
        settings_frame = ctk.CTkFrame(
            self,
            fg_color="#2D2D2D",
            corner_radius=20,
            border_width=1,
            border_color="#333333"
        )
        settings_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            settings_frame,
            text="",
            font=("Microsoft YaHei UI", 12),
            text_color="#888888"
        )
        self.status_label.pack(side="bottom", pady=10)
        
        # 密码保护设置
        password_frame = ctk.CTkFrame(
            settings_frame,
            fg_color="#1E1E1E",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        password_frame.pack(fill="x", padx=20, pady=15)
        
        password_label = ctk.CTkLabel(
            password_frame,
            text="密码保护",
            font=("Microsoft YaHei UI", 16, "bold"),
            text_color="#FFFFFF"
        )
        password_label.pack(pady=10)
        
        # 设置密码按钮
        self.password_btn = ctk.CTkButton(
            password_frame,
            text="修改密码" if self.password_manager.has_password else "设置密码",
            command=self._set_password,
            width=250,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#0066CC",
            hover_color="#0052A3",
            corner_radius=8
        )
        self.password_btn.pack(pady=5)
        
        # 移除密码按钮(仅在已设置密码时显示)
        if self.password_manager.has_password:
            remove_password_btn = ctk.CTkButton(
                password_frame,
                text="移除密码保护",
                command=self._remove_password,
                width=250,
                height=35,
                font=("Microsoft YaHei UI", 12),
                fg_color="#CC3333",
                hover_color="#A32929",
                corner_radius=8
            )
            remove_password_btn.pack(pady=5)
            
        # 开机自启动选项
        autostart_frame = ctk.CTkFrame(
            settings_frame,
            fg_color="#1E1E1E",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        autostart_frame.pack(fill="x", padx=20, pady=15)
        
        autostart_label = ctk.CTkLabel(
            autostart_frame,
            text="启动设置",
            font=("Microsoft YaHei UI", 16, "bold"),
            text_color="#FFFFFF"
        )
        autostart_label.pack(pady=10)
        
        self.autostart_var = tk.BooleanVar(value=check_autostart())
        autostart_switch = ctk.CTkSwitch(
            autostart_frame,
            text="开机自动启动",
            command=self._toggle_autostart,
            variable=self.autostart_var,
            font=("Microsoft YaHei UI", 12),
            text_color="#CCCCCC",
            button_color="#0066CC",
            button_hover_color="#0052A3",
            progress_color="#0066CC"
        )
        autostart_switch.pack(pady=10, padx=20, anchor="w")
        
        # 强制模式选项
        force_frame = ctk.CTkFrame(
            settings_frame,
            fg_color="#1E1E1E",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        force_frame.pack(fill="x", padx=20, pady=15)
        
        force_label = ctk.CTkLabel(
            force_frame,
            text="强制模式",
            font=("Microsoft YaHei UI", 16, "bold"),
            text_color="#FFFFFF"
        )
        force_label.pack(pady=10)
        
        self.force_var = tk.BooleanVar(value=parent.force_mode)
        force_switch = ctk.CTkSwitch(
            force_frame,
            text="开启后无法解除屏蔽",
            command=self._toggle_force_mode,
            variable=self.force_var,
            font=("Microsoft YaHei UI", 12),
            text_color="#CCCCCC",
            button_color="#0066CC",
            button_hover_color="#0052A3",
            progress_color="#0066CC"
        )
        force_switch.pack(pady=10, padx=20, anchor="w")
        
        # 白名单设置
        whitelist_frame = ctk.CTkFrame(
            settings_frame,
            fg_color="#1E1E1E",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        whitelist_frame.pack(fill="x", padx=20, pady=15)
        
        whitelist_label = ctk.CTkLabel(
            whitelist_frame,
            text="白名单",
            font=("Microsoft YaHei UI", 16, "bold"),
            text_color="#FFFFFF"
        )
        whitelist_label.pack(pady=10)
        
        # 白名单输入
        self.whitelist_entry = ctk.CTkEntry(
            whitelist_frame,
            placeholder_text="输入永不屏蔽的网站...",
            width=300,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#3D3D3D",
            border_color="#4D4D4D",
            placeholder_text_color="#666666"
        )
        self.whitelist_entry.pack(pady=5)
        
        # 添加到白名单按钮
        add_whitelist_btn = ctk.CTkButton(
            whitelist_frame,
            text="添加",
            command=self._add_whitelist,
            width=300,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#0066CC",
            hover_color="#0052A3",
            corner_radius=8
        )
        add_whitelist_btn.pack(pady=5)
        
        # 白名单列表
        whitelist_container = ctk.CTkFrame(
            whitelist_frame,
            fg_color="#1E1E1E",
            corner_radius=8,
            border_width=1,
            border_color="#333333"
        )
        whitelist_container.pack(fill="both", expand=True, pady=5)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(whitelist_container)
        scrollbar.pack(side="right", fill="y")
        
        # 白名单列表框
        self.whitelist_list = tk.Listbox(
            whitelist_container,
            yscrollcommand=scrollbar.set,
            selectmode="single",
            font=("Microsoft YaHei UI", 12),
            bg="#1E1E1E",
            fg="#FFFFFF",
            selectbackground="#0066CC",
            selectforeground="#FFFFFF",
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            height=6
        )
        self.whitelist_list.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        
        # 配置滚动条
        scrollbar.config(command=self.whitelist_list.yview)
        
        # 从白名单删除按钮
        delete_whitelist_btn = ctk.CTkButton(
            whitelist_frame,
            text="删除选中",
            command=self._delete_whitelist,
            width=300,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#CC3333",
            hover_color="#A32929",
            corner_radius=8
        )
        delete_whitelist_btn.pack(pady=5)
        
        # 更新白名单列表
        self._update_whitelist()
        
        # 确定按钮
        ok_button = ctk.CTkButton(
            settings_frame,
            text="确定",
            command=self.destroy,
            width=250,
            height=40,
            font=("Microsoft YaHei UI", 14),
            fg_color="#0066CC",
            hover_color="#0052A3",
            corner_radius=8
        )
        ok_button.pack(pady=20)
        
        # 使窗口模态
        self.transient(parent)
        self.grab_set()
        
    def _toggle_force_mode(self):
        self.parent.force_mode = self.force_var.get()
        self.status_label.configure(
            text="已开启强制模式" if self.parent.force_mode else "已关闭强制模式"
        )
        self.parent._save_config()
        
        # 如果开启强制模式,禁用暂停开关
        if self.parent.force_mode:
            self.parent.pause_var.set(False)
            self.parent.pause_switch.configure(state="disabled")
        else:
            self.parent.pause_switch.configure(state="normal")
        
    def _add_whitelist(self):
        website = self.whitelist_entry.get().strip()
        if website and website not in self.parent.whitelist:
            self.parent.whitelist.append(website)
            self.parent._save_config()
            self._update_whitelist()
            self.whitelist_entry.delete(0, tk.END)
            self.status_label.configure(text=f"已添加到白名单: {website}")
                
    def _delete_whitelist(self):
        selection = self.whitelist_list.curselection()
        if selection:
            index = selection[0]
            website = self.parent.whitelist[index]
            self.parent.whitelist.remove(website)
            self.parent._save_config()
            self._update_whitelist()
            self.status_label.configure(text=f"已从白名单移除: {website}")
                
    def _update_whitelist(self):
        self.whitelist_list.delete(0, tk.END)
        for website in self.parent.whitelist:
            self.whitelist_list.insert(tk.END, f"✨ {website}")
            
    def _toggle_autostart(self):
        success = set_autostart(self.autostart_var.get())
        if not success:
            self.autostart_var.set(not self.autostart_var.get())
            self.status_label.configure(text="开机自启动设置失败")
        else:
            self.status_label.configure(
                text="已开启开机自启动" if self.autostart_var.get() else "已关闭开机自启动"
            )

    def _set_password(self):
        PasswordDialog(self, self.password_manager, "set", self._on_password_set)
        
    def _on_password_set(self, success):
        if success:
            self.password_btn.configure(text="修改密码")
            self.status_label.configure(text="密码设置成功")
                
    def _remove_password(self):
        def on_verify(success):
            if success:
                if self.password_manager.remove_password():
                    self.password_btn.configure(text="设置密码")
                    self.status_label.configure(text="密码保护已移除")
                else:
                    self.status_label.configure(text="移除密码保护失败")
                        
        PasswordDialog(self, self.password_manager, "verify", on_verify)

class ScrollableFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # 配置滚动条样式
        self._scrollbar.configure(
            width=12,
            button_color="#1f538d",
            button_hover_color="#2666ad",
            fg_color="#232323"
        )

class ModernBlockerUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 初始化日志
        setup_logging()
        
        # 初始化功能组件
        self.password_manager = PasswordManager()
        self.focus_mode = FocusMode(self)
        self.app_blocker = AppBlocker()
        self.cloud_sync = CloudSync(self)
        self.recommender = WebsiteRecommender(self)
        self.time_unlocker = TimeUnlocker(self)
        self.hotkeys = GlobalHotkeys(self)
        
        # 注册全局快捷键
        self.hotkeys.register()
        
        # 基本设置
        self.title("网站访问管理")
        self.geometry("1200x800")
        self.minsize(1200, 800)
        
        # 设置主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # 初始化数据
        self.websites = {}
        self.block_times = {}
        self.whitelist = []
        self.force_mode = False
        self.silent_mode = False
        self.stats = {}
        self.blocked_apps = []
        
        # 预设分组
        self.groups = list(PRESET_WEBSITES.keys()) + ["自定义"]
        self.current_group = self.groups[0]
        
        # 预设规则
        self.rule_types = ["每天", "工作日", "周末", "自定义"]
        self.current_rule = "每天"
        
        # 设置快捷键
        self.bind("<Control-b>", lambda e: self._block_now())
        self.bind("<Control-p>", lambda e: self._toggle_pause())
        self.bind("<Control-i>", lambda e: self._import_config())
        self.bind("<Control-e>", lambda e: self._export_config())
        self.bind("<Control-s>", lambda e: self._show_stats())
        self.bind("<Control-w>", lambda e: self._add_website())
        self.bind("<Control-t>", lambda e: self._add_block_time())
        self.bind("<Control-f>", lambda e: self._show_focus_mode())
        self.bind("<Control-u>", lambda e: self._show_quick_unlock())
        self.bind("<Control-r>", lambda e: self._show_recommend())
        self.bind("<Delete>", lambda e: self._delete_selected())
        
        # 配置界面
        self._setup_ui()
        
        # 启动应用程序监控
        self.app_blocker.start_monitoring()
        
    def __del__(self):
        # 清理资源
        self.app_blocker.stop_monitoring()
        self.hotkeys.unregister()
        
    def _setup_ui(self):
        # 创建主容器
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=30, pady=(20, 10))
        
        # 创建左侧面板
        self.left_panel = ctk.CTkFrame(
            self.container,
            width=350,
            fg_color=THEME_COLORS["surface"],
            corner_radius=20,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        self.left_panel.pack(side="left", fill="y", padx=(0, 20))
        
        # 创建右侧面板
        self.right_panel = ctk.CTkFrame(
            self.container,
            fg_color=THEME_COLORS["surface"],
            corner_radius=20,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        self.right_panel.pack(side="right", fill="both", expand=True)
        
        # 创建状态栏
        self.status_bar = ctk.CTkFrame(
            self,
            height=40,
            fg_color=THEME_COLORS["surface"],
            corner_radius=0,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        self.status_bar.pack(side="bottom", fill="x", padx=30, pady=(0, 20))
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="就绪",
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"]
        )
        self.status_label.pack(side="left", padx=15)
        
        # 功能按钮区域
        buttons_frame = ctk.CTkFrame(
            self.status_bar,
            fg_color="transparent"
        )
        buttons_frame.pack(side="right", padx=15)
        
        # 专注模式按钮
        focus_btn = ctk.CTkButton(
            buttons_frame,
            text="专注模式",
            command=self._show_focus_mode,
            width=120,
            height=32,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS["primary_hover"],
            corner_radius=8
        )
        focus_btn.pack(side="left", padx=5, pady=4)
        
        # 快速解锁按钮
        unlock_btn = ctk.CTkButton(
            buttons_frame,
            text="快速解锁",
            command=self._show_quick_unlock,
            width=120,
            height=32,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS["primary_hover"],
            corner_radius=8
        )
        unlock_btn.pack(side="left", padx=5, pady=4)
        
        # 网站推荐按钮
        recommend_btn = ctk.CTkButton(
            buttons_frame,
            text="网站推荐",
            command=self._show_recommend,
            width=120,
            height=32,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS["primary_hover"],
            corner_radius=8
        )
        recommend_btn.pack(side="left", padx=5, pady=4)
        
        # 设置按钮
        settings_button = ctk.CTkButton(
            buttons_frame,
            text="⚙️ 设置",
            command=self._show_settings,
            width=120,
            height=32,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["secondary"],
            hover_color="#3D3D3D",
            corner_radius=8
        )
        settings_button.pack(side="left", padx=5, pady=4)
        
        self._setup_left_panel()
        self._setup_right_panel()
        self._load_config()
        
    def _setup_left_panel(self):
        # 标题
        title = ctk.CTkLabel(
            self.left_panel,
            text="功能设置",
            font=("Microsoft YaHei UI", 20, "bold"),
            text_color=THEME_COLORS["text"]
        )
        title.pack(pady=20)
        
        # 功能开关区域
        switch_frame = ctk.CTkFrame(
            self.left_panel,
            fg_color=THEME_COLORS["background"],
            corner_radius=15,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        switch_frame.pack(fill="x", padx=20, pady=10)
        
        # 开机自启动
        self.autostart_var = tk.BooleanVar(value=check_autostart())
        autostart_switch = ctk.CTkSwitch(
            switch_frame,
            text="开机自启动",
            command=self._toggle_autostart,
            variable=self.autostart_var,
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"],
            progress_color=THEME_COLORS["primary"],
            button_color=THEME_COLORS["primary"],
            button_hover_color=THEME_COLORS["primary_hover"]
        )
        autostart_switch.pack(pady=10, padx=20, anchor="w")
        
        # 强制模式
        self.force_var = tk.BooleanVar(value=self.force_mode)
        force_switch = ctk.CTkSwitch(
            switch_frame,
            text="强制模式",
            command=self._toggle_force_mode,
            variable=self.force_var,
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"],
            progress_color=THEME_COLORS["primary"],
            button_color=THEME_COLORS["primary"],
            button_hover_color=THEME_COLORS["primary_hover"]
        )
        force_switch.pack(pady=10, padx=20, anchor="w")
        
        # 静默模式
        self.silent_var = tk.BooleanVar(value=self.silent_mode)
        silent_switch = ctk.CTkSwitch(
            switch_frame,
            text="静默模式",
            command=self._toggle_silent_mode,
            variable=self.silent_var,
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"],
            progress_color=THEME_COLORS["primary"],
            button_color=THEME_COLORS["primary"],
            button_hover_color=THEME_COLORS["primary_hover"]
        )
        silent_switch.pack(pady=10, padx=20, anchor="w")
        
        # 暂停屏蔽
        self.pause_var = tk.BooleanVar(value=False)
        self.pause_switch = ctk.CTkSwitch(
            switch_frame,
            text="暂停屏蔽",
            command=self._toggle_pause,
            variable=self.pause_var,
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"],
            progress_color=THEME_COLORS["primary"],
            button_color=THEME_COLORS["primary"],
            button_hover_color=THEME_COLORS["primary_hover"],
            state="normal" if not self.force_mode else "disabled"
        )
        self.pause_switch.pack(pady=10, padx=20, anchor="w")
        
        # 功能按钮区域
        buttons_frame = ctk.CTkFrame(
            switch_frame,
            fg_color="transparent"
        )
        buttons_frame.pack(pady=10)
        
        # 统计图表按钮
        stats_btn = ctk.CTkButton(
            buttons_frame,
            text="查看统计图表",
            command=self._show_stats_charts,
            width=250,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS["primary_hover"],
            corner_radius=8
        )
        stats_btn.pack(pady=5)
        
        # 网站推荐按钮
        recommend_btn = ctk.CTkButton(
            buttons_frame,
            text="网站推荐",
            command=self._show_recommend,
            width=250,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS["primary_hover"],
            corner_radius=8
        )
        recommend_btn.pack(pady=5)
        
        # 应用程序屏蔽按钮
        app_btn = ctk.CTkButton(
            buttons_frame,
            text="应用程序屏蔽",
            command=self._show_app_blocker,
            width=250,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS["primary_hover"],
            corner_radius=8
        )
        app_btn.pack(pady=5)
        
        # 云端同步按钮
        cloud_btn = ctk.CTkButton(
            buttons_frame,
            text="云端同步",
            command=self._show_cloud_sync,
            width=250,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS["primary_hover"],
            corner_radius=8
        )
        cloud_btn.pack(pady=5)
        
        # 网站管理区域
        website_frame = ctk.CTkFrame(
            self.left_panel,
            fg_color=THEME_COLORS["background"],
            corner_radius=15,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        website_frame.pack(fill="x", padx=20, pady=10)
        
        # 分组选择
        group_label = ctk.CTkLabel(
            website_frame,
            text="选择分组",
            font=("Microsoft YaHei UI", 14),
            text_color="#CCCCCC"
        )
        group_label.pack(pady=(15, 5))
        
        self.group_var = tk.StringVar(value=self.current_group)
        group_menu = ctk.CTkOptionMenu(
            website_frame,
            values=self.groups,
            variable=self.group_var,
            command=self._on_group_change,
            width=250,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#3D3D3D",
            button_color="#4D4D4D",
            button_hover_color="#5D5D5D",
            dropdown_fg_color="#2D2D2D",
            dropdown_hover_color="#4D4D4D",
            dropdown_font=("Microsoft YaHei UI", 12)
        )
        group_menu.pack(pady=5)
        
        # 网站输入
        website_label = ctk.CTkLabel(
            website_frame,
            text="添加网站",
            font=("Microsoft YaHei UI", 14),
            text_color="#CCCCCC"
        )
        website_label.pack(pady=(15, 5))
        
        self.website_entry = ctk.CTkEntry(
            website_frame,
            placeholder_text="输入要屏蔽的网站...",
            width=250,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#3D3D3D",
            border_color="#4D4D4D",
            placeholder_text_color="#666666"
        )
        self.website_entry.pack(pady=5)
        
        add_website_btn = ctk.CTkButton(
            website_frame,
            text="添加",
            command=self._add_website,
            width=250,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#0066CC",
            hover_color="#0052A3",
            corner_radius=8
        )
        add_website_btn.pack(pady=5)
        
        # 一键导入按钮
        quick_import_btn = ctk.CTkButton(
            website_frame,
            text="一键导入常用网站",
            command=self._quick_import,
            width=250,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#2D2D2D",
            hover_color="#3D3D3D",
            corner_radius=8
        )
        quick_import_btn.pack(pady=(5, 15))
        
        # 时间规则区域
        time_frame = ctk.CTkFrame(
            self.left_panel,
            fg_color="#2D2D2D",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        time_frame.pack(fill="x", padx=20, pady=10)
        
        # 规则类型选择
        rule_label = ctk.CTkLabel(
            time_frame,
            text="选择规则",
            font=("Microsoft YaHei UI", 14),
            text_color="#CCCCCC"
        )
        rule_label.pack(pady=(15, 5))
        
        self.rule_var = tk.StringVar(value=self.current_rule)
        rule_menu = ctk.CTkOptionMenu(
            time_frame,
            values=self.rule_types,
            variable=self.rule_var,
            command=self._on_rule_change,
            width=250,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#3D3D3D",
            button_color="#4D4D4D",
            button_hover_color="#5D5D5D",
            dropdown_fg_color="#2D2D2D",
            dropdown_hover_color="#4D4D4D",
            dropdown_font=("Microsoft YaHei UI", 12)
        )
        rule_menu.pack(pady=5)
        
        # 时间选择
        time_label = ctk.CTkLabel(
            time_frame,
            text="添加时间",
            font=("Microsoft YaHei UI", 14),
            text_color="#CCCCCC"
        )
        time_label.pack(pady=(15, 5))
        
        spinbox_frame = ctk.CTkFrame(time_frame, fg_color="transparent")
        spinbox_frame.pack(pady=5)
        
        # 小时输入框
        self.hour_spinbox = ctk.CTkEntry(
            spinbox_frame,
            width=70,
            height=35,
            justify="center",
            font=("Microsoft YaHei UI", 14),
            fg_color="#3D3D3D",
            border_color="#4D4D4D"
        )
        self.hour_spinbox.pack(side="left", padx=2)
        self.hour_spinbox.insert(0, "00")
        
        ctk.CTkLabel(
            spinbox_frame,
            text=":",
            font=("Microsoft YaHei UI", 14),
            text_color="#CCCCCC"
        ).pack(side="left")
        
        # 分钟输入框
        self.minute_spinbox = ctk.CTkEntry(
            spinbox_frame,
            width=70,
            height=35,
            justify="center",
            font=("Microsoft YaHei UI", 14),
            fg_color="#3D3D3D",
            border_color="#4D4D4D"
        )
        self.minute_spinbox.pack(side="left", padx=2)
        self.minute_spinbox.insert(0, "00")
        
        ctk.CTkLabel(
            spinbox_frame,
            text=":",
            font=("Microsoft YaHei UI", 14),
            text_color="#CCCCCC"
        ).pack(side="left")
        
        # 秒钟输入框
        self.second_spinbox = ctk.CTkEntry(
            spinbox_frame,
            width=70,
            height=35,
            justify="center",
            font=("Microsoft YaHei UI", 14),
            fg_color="#3D3D3D",
            border_color="#4D4D4D"
        )
        self.second_spinbox.pack(side="left", padx=2)
        self.second_spinbox.insert(0, "00")
        
        add_time_btn = ctk.CTkButton(
            time_frame,
            text="添加",
            command=self._add_block_time,
            width=250,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#0066CC",
            hover_color="#0052A3",
            corner_radius=8
        )
        add_time_btn.pack(pady=(15, 15))
        
    def _on_group_change(self, choice):
        self.current_group = choice
        self._update_lists()
        
    def _on_rule_change(self, choice):
        self.current_rule = choice
        self._update_lists()
        
    def _quick_import(self):
        common_sites = {
            "社交": [
                "facebook.com", "twitter.com", "instagram.com",
                "tiktok.com", "weibo.com", "zhihu.com",
                "linkedin.com", "pinterest.com"
            ],
            "视频娱乐": [
                "youtube.com", "netflix.com", "bilibili.com",
                "douyu.com", "huya.com", "iqiyi.com",
                "youku.com", "twitch.tv"
            ],
            "游戏平台": [
                "steam.com", "epicgames.com", "origin.com",
                "blizzard.com", "ubisoft.com", "ea.com",
                "battlenet.com", "gog.com", "4399.com"
            ],
            "购物网站": [
                "taobao.com", "jd.com", "amazon.com",
                "tmall.com", "pinduoduo.com", "ebay.com",
                "aliexpress.com", "walmart.com"
            ],
            "新闻资讯": [
                "news.qq.com", "sina.com.cn", "163.com",
                "sohu.com", "ifeng.com", "thepaper.cn",
                "cnn.com", "bbc.com"
            ],
            "在线聊天": [
                "wx.qq.com", "web.telegram.org", "discord.com",
                "messenger.com", "slack.com", "teams.microsoft.com",
                "meet.google.com", "zoom.us"
            ]
        }
        
        count = 0
        for group, sites in common_sites.items():
            if group not in self.websites:
                self.websites[group] = []
            for site in sites:
                if site not in self.websites[group]:
                    self.websites[group].append(site)
                    count += 1
                    
        self._save_config()
        self._update_lists()
        self.status_label.configure(text=f"已导入 {count} 个常用网站")
        
    def _add_website(self):
        website = self.website_entry.get().strip()
        if website:
            if self.current_group not in self.websites:
                self.websites[self.current_group] = []
            if website not in self.websites[self.current_group]:
                self.websites[self.current_group].append(website)
                self._save_config()
                self._update_lists()
                self.website_entry.delete(0, tk.END)
                self.status_label.configure(text=f"已添加网站: {website}")
            else:
                self.status_label.configure(text="该网站已存在于当前分组")
        else:
            self.status_label.configure(text="请输入网站地址")
            
    def _add_block_time(self):
        try:
            hour = int(self.hour_spinbox.get())
            minute = int(self.minute_spinbox.get())
            second = int(self.second_spinbox.get())
            
            if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                self.status_label.configure(text="无效的时间格式")
                return
                
            time = f"{hour:02d}:{minute:02d}:{second:02d}"
            
            if self.current_rule not in self.block_times:
                self.block_times[self.current_rule] = []
                
            if time not in self.block_times[self.current_rule]:
                self.block_times[self.current_rule].append(time)
                self._save_config()
                self._update_lists()
                
                self.hour_spinbox.delete(0, tk.END)
                self.hour_spinbox.insert(0, "00")
                self.minute_spinbox.delete(0, tk.END)
                self.minute_spinbox.insert(0, "00")
                self.second_spinbox.delete(0, tk.END)
                self.second_spinbox.insert(0, "00")
                
                self.status_label.configure(text=f"已添加屏蔽时间: {time}")
            else:
                self.status_label.configure(text="该时间已存在于当前规则")
                
        except ValueError:
            self.status_label.configure(text="时间格式错误")
            
    def _load_config(self):
        try:
            if os.path.exists("blocker_config.json"):
                with open("blocker_config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.websites = config.get("websites", {})
                    self.block_times = config.get("block_times", {})
                    self.whitelist = config.get("whitelist", [])
                    self.force_mode = config.get("force_mode", False)
                    self.silent_mode = config.get("silent_mode", False)
                    self.stats = config.get("stats", {})
                    self.blocked_apps = config.get("blocked_apps", [])
            self._update_lists()
            self.status_label.configure(text="配置加载完成")
            logging.info("配置加载成功")
        except Exception as e:
            self.websites = {}
            self.block_times = {}
            self.whitelist = []
            self.force_mode = False
            self.silent_mode = False
            self.stats = {}
            self.blocked_apps = []
            self.status_label.configure(text="配置加载失败")
            logging.error(f"配置加载失败: {str(e)}")
            
    def _save_config(self):
        try:
            config = {
                "websites": self.websites,
                "block_times": self.block_times,
                "whitelist": self.whitelist,
                "force_mode": self.force_mode,
                "silent_mode": self.silent_mode,
                "stats": self.stats,
                "blocked_apps": self.blocked_apps
            }
            with open("blocker_config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.status_label.configure(text="配置保存成功")
            logging.info("配置保存成功")
        except Exception as e:
            self.status_label.configure(text="配置保存失败")
            logging.error(f"配置保存失败: {str(e)}")
            
    def _update_lists(self):
        # 更新网站列表
        self.website_list.delete(0, tk.END)
        if self.current_group in self.websites:
            for website in self.websites[self.current_group]:
                self.website_list.insert(tk.END, f"🌐 {website}")
                
        # 更新时间列表
        self.time_list.delete(0, tk.END)
        if self.current_rule in self.block_times:
            for time in self.block_times[self.current_rule]:
                self.time_list.insert(tk.END, f"⏰ {time}")
        
    def _show_settings(self):
        def on_verify(success):
            if success:
                settings_window = SettingsWindow(self)
                settings_window.focus()
                
        if self.password_manager.has_password:
            PasswordDialog(self, self.password_manager, "verify", on_verify)
        else:
            settings_window = SettingsWindow(self)
            settings_window.focus()
        
    def _setup_right_panel(self):
        # 标题
        title = ctk.CTkLabel(
            self.right_panel,
            text="已添加规则",
            font=("Microsoft YaHei UI", 20, "bold"),
            text_color="#FFFFFF"
        )
        title.pack(pady=20)
        
        # 网站列表区域
        website_frame = ctk.CTkFrame(
            self.right_panel,
            fg_color="#2D2D2D",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        website_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        website_label = ctk.CTkLabel(
            website_frame,
            text="已添加的网站",
            font=("Microsoft YaHei UI", 14),
            text_color="#CCCCCC"
        )
        website_label.pack(pady=(15, 5))
        
        # 创建一个带滚动条的列表框容器
        list_container = ctk.CTkFrame(
            website_frame,
            fg_color="#1E1E1E",
            corner_radius=8,
            border_width=1,
            border_color="#333333"
        )
        list_container.pack(fill="both", expand=True, padx=15, pady=10)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")
        
        # 网站列表框
        self.website_list = tk.Listbox(
            list_container,
            yscrollcommand=scrollbar.set,
            selectmode="single",
            font=("Microsoft YaHei UI", 12),
            bg="#1E1E1E",
            fg="#FFFFFF",
            selectbackground="#0066CC",
            selectforeground="#FFFFFF",
            borderwidth=0,
            highlightthickness=0,
            activestyle="none"
        )
        self.website_list.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        
        # 配置滚动条
        scrollbar.config(command=self.website_list.yview)
        
        # 删除网站按钮
        delete_website_btn = ctk.CTkButton(
            website_frame,
            text="删除选中",
            command=self._delete_website,
            width=200,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#CC3333",
            hover_color="#A32929",
            corner_radius=8
        )
        delete_website_btn.pack(pady=(5, 15))
        
        # 时间列表区域
        time_frame = ctk.CTkFrame(
            self.right_panel,
            fg_color="#2D2D2D",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        time_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        time_label = ctk.CTkLabel(
            time_frame,
            text="已添加的时间",
            font=("Microsoft YaHei UI", 14),
            text_color="#CCCCCC"
        )
        time_label.pack(pady=(15, 5))
        
        # 创建一个带滚动条的列表框容器
        time_container = ctk.CTkFrame(
            time_frame,
            fg_color="#1E1E1E",
            corner_radius=8,
            border_width=1,
            border_color="#333333"
        )
        time_container.pack(fill="both", expand=True, padx=15, pady=10)
        
        # 滚动条
        time_scrollbar = ttk.Scrollbar(time_container)
        time_scrollbar.pack(side="right", fill="y")
        
        # 时间列表框
        self.time_list = tk.Listbox(
            time_container,
            yscrollcommand=time_scrollbar.set,
            selectmode="single",
            font=("Microsoft YaHei UI", 12),
            bg="#1E1E1E",
            fg="#FFFFFF",
            selectbackground="#0066CC",
            selectforeground="#FFFFFF",
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            height=6
        )
        self.time_list.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        
        # 配置滚动条
        time_scrollbar.config(command=self.time_list.yview)
        
        # 删除时间按钮
        delete_time_btn = ctk.CTkButton(
            time_frame,
            text="删除选中",
            command=self._delete_time,
            width=200,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color="#CC3333",
            hover_color="#A32929",
            corner_radius=8
        )
        delete_time_btn.pack(pady=(5, 15))
        
    def _delete_website(self):
        selection = self.website_list.curselection()
        if selection:
            index = selection[0]
            website = self.websites[self.current_group][index]
            self.websites[self.current_group].remove(website)
            self._save_config()
            self._update_lists()
            self.status_label.configure(text=f"已删除网站: {website}")
            
    def _delete_time(self):
        selection = self.time_list.curselection()
        if selection:
            index = selection[0]
            time = self.block_times[self.current_rule][index]
            self.block_times[self.current_rule].remove(time)
            self._save_config()
            self._update_lists()
            self.status_label.configure(text=f"已删除时间: {time}")
            
    def _block_now(self):
        try:
            if hasattr(self, 'blocker'):
                self.blocker.modify_hosts()
                self.status_label.configure(text="已立即生效屏蔽设置")
                logging.info("手动触发屏蔽设置")
            else:
                self.blocker = WebsiteBlocker()
                self.blocker.websites = self.websites
                self.blocker.modify_hosts()
                self.status_label.configure(text="已立即生效屏蔽设置")
                logging.info("手动触发屏蔽设置")
        except Exception as e:
            self.status_label.configure(text="立即屏蔽失败，请检查权限")
            logging.error(f"屏蔽失败: {str(e)}")
            
    def _toggle_pause(self):
        # 如果开启了强制模式,不允许暂停
        if self.force_mode:
            self.pause_var.set(False)
            self.status_label.configure(text="强制模式下无法暂停屏蔽")
            return
            
        try:
            if hasattr(self, 'blocker'):
                if self.pause_var.get():
                    self.blocker.websites = []
                    self.blocker.modify_hosts()
                    self.status_label.configure(text="已暂停屏蔽")
                    logging.info("屏蔽已暂停")
                else:
                    self.blocker.websites = self.websites
                    self.blocker.modify_hosts()
                    self.status_label.configure(text="已恢复屏蔽")
                    logging.info("屏蔽已恢复")
            else:
                self.blocker = WebsiteBlocker()
                self.blocker.websites = [] if self.pause_var.get() else self.websites
                self.blocker.modify_hosts()
                self.status_label.configure(text="已暂停屏蔽" if self.pause_var.get() else "已恢复屏蔽")
                logging.info("屏蔽已暂停" if self.pause_var.get() else "屏蔽已恢复")
        except Exception as e:
            self.status_label.configure(text="操作失败，请检查权限")
            self.pause_var.set(not self.pause_var.get())
            logging.error(f"切换暂停状态失败: {str(e)}")
            
    def _import_config(self):
        try:
            file_path = tk.filedialog.askopenfilename(
                title="选择配置文件",
                filetypes=[("JSON文件", "*.json")]
            )
            if file_path:
                with open(file_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.websites = config.get("websites", {})
                    self.block_times = config.get("block_times", {})
                    self.whitelist = config.get("whitelist", [])
                    self.force_mode = config.get("force_mode", False)
                    self.silent_mode = config.get("silent_mode", False)
                    self.stats = config.get("stats", {})
                    self.blocked_apps = config.get("blocked_apps", [])
                    self.status_label.configure(text="配置导入成功")
        except Exception as e:
            self.status_label.configure(text="配置导入失败")
            
    def _export_config(self):
        try:
            file_path = tk.filedialog.asksaveasfilename(
                title="保存配置文件",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json")]
            )
            if file_path:
                config = {
                    "websites": self.websites,
                    "block_times": self.block_times,
                    "whitelist": self.whitelist,
                    "force_mode": self.force_mode,
                    "silent_mode": self.silent_mode,
                    "stats": self.stats,
                    "blocked_apps": self.blocked_apps
                }
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                self.status_label.configure(text="配置导出成功")
        except Exception as e:
            self.status_label.configure(text="配置导出失败")
            
    def _show_stats(self):
        stats_window = StatsWindow(self)
        stats_window.focus()
        
    def _delete_selected(self):
        # 根据当前焦点决定删除网站还是时间
        focused = self.focus_get()
        if focused == self.website_list:
            self._delete_website()
        elif focused == self.time_list:
            self._delete_time()
            
    def _update_stats(self, website):
        if website not in self.stats:
            self.stats[website] = {
                "block_count": 0,
                "last_blocked": None,
                "total_blocked_time": 0
            }
        self.stats[website]["block_count"] += 1
        self.stats[website]["last_blocked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save_config()
        
        # 在非静默模式下显示通知
        if not self.silent_mode:
            self.status_label.configure(text=f"已屏蔽网站: {website}")

    def _show_backup(self):
        backup_window = BackupWindow(self)
        backup_window.focus()

    def _show_stats_charts(self):
        stats_chart_window = StatsChartWindow(self)
        stats_chart_window.focus()

    def _toggle_autostart(self):
        success = set_autostart(self.autostart_var.get())
        if not success:
            self.autostart_var.set(not self.autostart_var.get())
            self.status_label.configure(text="开机自启动设置失败")
        else:
            self.status_label.configure(
                text="已开启开机自启动" if self.autostart_var.get() else "已关闭开机自启动"
            )
            
    def _toggle_force_mode(self):
        self.force_mode = self.force_var.get()
        self.status_label.configure(
            text="已开启强制模式" if self.force_mode else "已关闭强制模式"
        )
        self._save_config()
        
        # 如果开启强制模式,禁用暂停开关
        if self.force_mode:
            self.pause_var.set(False)
            self.pause_switch.configure(state="disabled")
        else:
            self.pause_switch.configure(state="normal")
            
    def _toggle_silent_mode(self):
        self.silent_mode = self.silent_var.get()
        self.status_label.configure(
            text="已开启静默模式" if self.silent_mode else "已关闭静默模式"
        )
        self._save_config()

    def _show_focus_mode(self):
        """显示专注模式窗口"""
        FocusModeWindow(self)
        
    def _show_quick_unlock(self):
        """显示快速解锁窗口"""
        QuickUnlockWindow(self)
        
    def _show_recommend(self):
        """显示网站推荐窗口"""
        RecommendWindow(self)
        
    def _show_cloud_sync(self):
        """执行云端同步"""
        success, message = self.cloud_sync.backup_to_cloud()
        self.status_label.configure(text=message)

    def _show_app_blocker(self):
        """显示应用程序屏蔽窗口"""
        AppBlockerWindow(self)

class StatsChartWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        # 基本设置
        self.title("统计图表")
        self.geometry("1000x600")
        self.minsize(1000, 600)
        
        # 设置主题
        self.configure(fg_color="#1E1E1E")
        
        # 标题
        title = ctk.CTkLabel(
            self,
            text="统计图表",
            font=("Microsoft YaHei UI", 24, "bold"),
            text_color="#FFFFFF"
        )
        title.pack(pady=20)
        
        # 主容器
        main_frame = ctk.CTkFrame(
            self,
            fg_color="#2D2D2D",
            corner_radius=20,
            border_width=1,
            border_color="#333333"
        )
        main_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        
        # 创建左右布局
        left_frame = ctk.CTkFrame(
            main_frame,
            fg_color="transparent"
        )
        left_frame.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        
        right_frame = ctk.CTkFrame(
            main_frame,
            fg_color="transparent"
        )
        right_frame.pack(side="right", fill="both", expand=True, padx=15, pady=15)
        
        # 折线图区域
        line_frame = ctk.CTkFrame(
            left_frame,
            fg_color="#1E1E1E",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        line_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        line_title = ctk.CTkLabel(
            line_frame,
            text="屏蔽趋势",
            font=("Microsoft YaHei UI", 16, "bold"),
            text_color="#FFFFFF"
        )
        line_title.pack(pady=10)
        
        # 创建折线图画布
        self.line_canvas = tk.Canvas(
            line_frame,
            bg="#1E1E1E",
            highlightthickness=0
        )
        self.line_canvas.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # 扇形图区域
        pie_frame = ctk.CTkFrame(
            right_frame,
            fg_color="#1E1E1E",
            corner_radius=15,
            border_width=1,
            border_color="#333333"
        )
        pie_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        pie_title = ctk.CTkLabel(
            pie_frame,
            text="分组占比",
            font=("Microsoft YaHei UI", 16, "bold"),
            text_color="#FFFFFF"
        )
        pie_title.pack(pady=10)
        
        # 创建扇形图画布
        self.pie_canvas = tk.Canvas(
            pie_frame,
            bg="#1E1E1E",
            highlightthickness=0
        )
        self.pie_canvas.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # 绘制图表
        self._draw_charts(parent.stats, parent.websites)
        
        # 使窗口模态
        self.transient(parent)
        self.grab_set()
        
    def _draw_line_chart(self, stats):
        # 清空画布
        self.line_canvas.delete("all")
        
        # 获取画布尺寸
        width = self.line_canvas.winfo_width()
        height = self.line_canvas.winfo_height()
        
        # 设置边距
        margin = 40
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin
        
        # 获取数据
        dates = []
        counts = []
        for website, data in stats.items():
            if data["last_blocked"]:
                date = datetime.strptime(data["last_blocked"], "%Y-%m-%d %H:%M:%S").date()
                if date not in dates:
                    dates.append(date)
                    counts.append(1)
                else:
                    index = dates.index(date)
                    counts[index] += 1
                    
        if not dates:
            # 无数据时显示提示
            self.line_canvas.create_text(
                width/2,
                height/2,
                text="暂无数据",
                font=("Microsoft YaHei UI", 14),
                fill="#666666"
            )
            return
            
        # 排序数据
        dates, counts = zip(*sorted(zip(dates, counts)))
        
        # 计算坐标
        x_step = chart_width / (len(dates) - 1) if len(dates) > 1 else chart_width
        y_scale = chart_height / (max(counts) if max(counts) > 0 else 1)
        
        # 绘制坐标轴
        self.line_canvas.create_line(
            margin, height - margin,
            width - margin, height - margin,
            fill="#666666"
        )
        self.line_canvas.create_line(
            margin, height - margin,
            margin, margin,
            fill="#666666"
        )
        
        # 绘制折线
        points = []
        for i, (date, count) in enumerate(zip(dates, counts)):
            x = margin + i * x_step
            y = height - margin - count * y_scale
            points.extend([x, y])
            
            # 绘制数据点
            self.line_canvas.create_oval(
                x-4, y-4, x+4, y+4,
                fill="#0066CC",
                outline="#FFFFFF"
            )
            
            # 绘制日期标签
            self.line_canvas.create_text(
                x,
                height - margin + 20,
                text=date.strftime("%m-%d"),
                font=("Microsoft YaHei UI", 10),
                fill="#CCCCCC",
                angle=45
            )
            
        # 绘制折线
        if len(points) >= 4:
            self.line_canvas.create_line(
                points,
                fill="#0066CC",
                width=2,
                smooth=True
            )
            
    def _draw_pie_chart(self, websites):
        # 清空画布
        self.pie_canvas.delete("all")
        
        # 获取画布尺寸
        width = self.pie_canvas.winfo_width()
        height = self.pie_canvas.winfo_height()
        
        # 计算饼图大小
        pie_radius = min(width, height) * 0.35
        center_x = width / 2
        center_y = height / 2
        
        # 统计各分组的网站数量
        group_counts = {}
        total = 0
        for group, sites in websites.items():
            count = len(sites)
            if count > 0:
                group_counts[group] = count
                total += count
                
        if not group_counts:
            # 无数据时显示提示
            self.pie_canvas.create_text(
                width/2,
                height/2,
                text="暂无数据",
                font=("Microsoft YaHei UI", 14),
                fill="#666666"
            )
            return
            
        # 定义颜色
        colors = ["#0066CC", "#00CC66", "#CC6600", "#CC0066", "#6600CC", "#66CC00"]
        
        # 绘制扇形
        start_angle = 0
        legend_y = 50
        for i, (group, count) in enumerate(group_counts.items()):
            # 计算扇形角度
            angle = count / total * 360
            
            # 绘制扇形
            self.pie_canvas.create_arc(
                center_x - pie_radius,
                center_y - pie_radius,
                center_x + pie_radius,
                center_y + pie_radius,
                start=start_angle,
                extent=angle,
                fill=colors[i % len(colors)],
                outline="#FFFFFF"
            )
            
            # 绘制图例
            legend_x = width - 150
            self.pie_canvas.create_rectangle(
                legend_x,
                legend_y,
                legend_x + 20,
                legend_y + 20,
                fill=colors[i % len(colors)],
                outline="#FFFFFF"
            )
            
            self.pie_canvas.create_text(
                legend_x + 30,
                legend_y + 10,
                text=f"{group} ({count})",
                font=("Microsoft YaHei UI", 12),
                fill="#FFFFFF",
                anchor="w"
            )
            
            start_angle += angle
            legend_y += 30
            
    def _draw_charts(self, stats, websites):
        # 绑定重绘事件
        self.line_canvas.bind("<Configure>", lambda e: self._draw_line_chart(stats))
        self.pie_canvas.bind("<Configure>", lambda e: self._draw_pie_chart(websites))
        
        # 初始绘制
        self._draw_line_chart(stats)
        self._draw_pie_chart(websites)

class WebsiteBlocker:
    def __init__(self):
        self.load_config()
        self.setup_tray()
        self.running = True
        logging.info("网站访问管理已启动")
        
    def load_config(self):
        try:
            if os.path.exists("blocker_config.json"):
                with open("blocker_config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.websites = config.get("websites", {})
                    self.block_times = config.get("block_times", {})
                    self.whitelist = config.get("whitelist", [])
                    self.force_mode = config.get("force_mode", False)
                    self.silent_mode = config.get("silent_mode", False)
                    self.stats = config.get("stats", {})
            else:
                self.websites = {}
                self.block_times = {}
                self.whitelist = []
                self.force_mode = False
                self.silent_mode = False
                self.stats = {}
        except Exception as e:
            self.websites = {}
            self.block_times = {}
            self.whitelist = []
            self.force_mode = False
            self.silent_mode = False
            self.stats = {}
            
    def create_transparent_icon(self):
        # 创建透明图标
        image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
        return image
        
    def setup_tray(self):
        image = self.create_transparent_icon()
        self.icon = pystray.Icon(
            "website_blocker",
            image,
            "网站访问管理",
            menu=self.create_menu()
        )
        
    def create_menu(self):
        return pystray.Menu(
            pystray.MenuItem("设置", self.show_settings),
            pystray.MenuItem("退出", self.quit_app)
        )
        
    def show_settings(self, icon, item):
        # 在主线程中创建UI
        if hasattr(self, 'ui') and self.ui.winfo_exists():
            self.ui.lift()
            self.ui.focus_force()
        else:
            self.ui = ModernBlockerUI()
            self.ui.mainloop()
        
    def modify_hosts(self):
        try:
            handle = win32security.GetCurrentProcess()
            token = win32security.OpenProcessToken(handle, win32con.TOKEN_ALL_ACCESS)
            
            # 读取现有内容
            current_content = ""
            if os.path.exists(HOSTS_PATH):
                with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
                    current_content = f.read()
            
            # 备份hosts文件
            backup_path = HOSTS_PATH + ".backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(current_content)
            
            # 移除现有的屏蔽条目
            lines = []
            for line in current_content.splitlines():
                if not line.strip() or line.startswith("#"):
                    lines.append(line)
                    continue
                    
                if not any(site in line for site in self.websites):
                    lines.append(line)
            
            # 添加新的屏蔽条目
            for group, sites in self.websites.items():
                lines.append(f"\n# {group} 分组")
                for site in sites:
                    # 处理域名格式
                    site = site.lower().strip()
                    if site.startswith("http://"):
                        site = site[7:]
                    elif site.startswith("https://"):
                        site = site[8:]
                    
                    # 移除路径部分
                    site = site.split('/')[0]
                    
                    # 添加带www和不带www的版本
                    if not site.startswith("www."):
                        lines.append(f"127.0.0.1 www.{site}")
                    lines.append(f"127.0.0.1 {site}")
            
            # 写入新内容
            try:
                with open(HOSTS_PATH, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                # 刷新DNS缓存
                os.system('ipconfig /flushdns')
                
                # 验证修改是否成功
                with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
                    new_content = f.read()
                if all(site in new_content for group in self.websites.values() for site in group):
                    logging.info(f"hosts文件已更新，屏蔽 {sum(len(sites) for sites in self.websites.values())} 个网站")
                    self._update_stats(site)  # 更新统计信息
                else:
                    raise Exception("hosts文件验证失败")
                    
            except Exception as write_error:
                # 如果写入失败，恢复备份
                with open(HOSTS_PATH, 'w', encoding='utf-8') as f:
                    f.write(current_content)
                raise write_error
                
        except Exception as e:
            error_msg = str(e)
            if "拒绝访问" in error_msg:
                logging.error("修改hosts文件失败: 权限不足，请以管理员身份运行程序")
            elif "找不到文件" in error_msg:
                logging.error("修改hosts文件失败: hosts文件不存在")
            else:
                logging.error(f"修改hosts文件失败: {error_msg}")
            return False
            
        return True
            
    def schedule_jobs(self):
        schedule.clear()
        for time in self.block_times:
            schedule.every().day.at(time).do(self.modify_hosts)
            
    def run_schedule(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)
            
    def quit_app(self, icon, item):
        self.running = False
        icon.stop()
        logging.info("网站访问管理已退出")
        sys.exit(0)
        
    def run(self):
        self.schedule_jobs()
        schedule_thread = threading.Thread(target=self.run_schedule)
        schedule_thread.daemon = True
        schedule_thread.start()
        self.icon.run()

class StatsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        # 基本设置
        self.title("屏蔽统计")
        self.geometry("800x600")
        self.minsize(800, 600)
        
        # 设置主题
        self.configure(fg_color="#1E1E1E")
        
        # 标题
        title = ctk.CTkLabel(
            self,
            text="屏蔽统计",
            font=("Microsoft YaHei UI", 24, "bold"),
            text_color="#FFFFFF"
        )
        title.pack(pady=20)
        
        # 统计容器
        stats_frame = ctk.CTkFrame(
            self,
            fg_color="#2D2D2D",
            corner_radius=20,
            border_width=1,
            border_color="#333333"
        )
        stats_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        
        # 创建表格
        self._create_table(stats_frame, parent.stats)
        
        # 导出按钮
        export_btn = ctk.CTkButton(
            stats_frame,
            text="导出统计报告",
            command=lambda: self._export_stats(parent.stats),
            width=250,
            height=40,
            font=("Microsoft YaHei UI", 14),
            fg_color="#0066CC",
            hover_color="#0052A3",
            corner_radius=8
        )
        export_btn.pack(pady=20)
        
        # 使窗口模态
        self.transient(parent)
        self.grab_set()
        
    def _create_table(self, parent, stats):
        # 创建表格头部
        headers = ["网站", "屏蔽次数", "最后屏蔽时间"]
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=10)
        
        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                header_frame,
                text=header,
                font=("Microsoft YaHei UI", 14, "bold"),
                text_color="#FFFFFF"
            )
            label.grid(row=0, column=i, padx=20, pady=5, sticky="w")
            
        # 创建表格内容容器(带滚动条)
        content_container = ctk.CTkScrollableFrame(
            parent,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
            scrollbar_button_color="#0066CC",
            scrollbar_button_hover_color="#0052A3"
        )
        content_container.pack(fill="both", expand=True, padx=20)
        
        # 创建表格内容
        for i, (website, data) in enumerate(stats.items()):
            row_frame = ctk.CTkFrame(
                content_container,
                fg_color="#2D2D2D" if i % 2 == 0 else "#262626",
                corner_radius=8
            )
            row_frame.pack(fill="x", pady=2)
            
            # 网站
            ctk.CTkLabel(
                row_frame,
                text=website,
                font=("Microsoft YaHei UI", 12),
                text_color="#FFFFFF"
            ).grid(row=0, column=0, padx=20, pady=8, sticky="w")
            
            # 屏蔽次数
            ctk.CTkLabel(
                row_frame,
                text=str(data["block_count"]),
                font=("Microsoft YaHei UI", 12),
                text_color="#FFFFFF"
            ).grid(row=0, column=1, padx=20, pady=8, sticky="w")
            
            # 最后屏蔽时间
            ctk.CTkLabel(
                row_frame,
                text=data["last_blocked"] or "从未屏蔽",
                font=("Microsoft YaHei UI", 12),
                text_color="#FFFFFF"
            ).grid(row=0, column=2, padx=20, pady=8, sticky="w")
            
    def _export_stats(self, stats):
        try:
            file_path = tk.filedialog.asksaveasfilename(
                title="保存统计报告",
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt")]
            )
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("网站访问管理 - 屏蔽统计报告\n")
                    f.write("=" * 50 + "\n\n")
                    f.write("生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
                    
                    for website, data in stats.items():
                        f.write(f"网站: {website}\n")
                        f.write(f"屏蔽次数: {data['block_count']}\n")
                        f.write(f"最后屏蔽时间: {data['last_blocked'] or '从未屏蔽'}\n")
                        f.write("-" * 30 + "\n")
                        
                self.status_label = ctk.CTkLabel(
                    self,
                    text="统计报告导出成功",
                    font=("Microsoft YaHei UI", 10),
                    text_color="#888888"
                )
                self.status_label.pack(pady=10)
        except Exception as e:
            self.status_label = ctk.CTkLabel(
                self,
                text="统计报告导出失败",
                font=("Microsoft YaHei UI", 10),
                text_color="#888888"
            )
            self.status_label.pack(pady=10)

class FocusMode:
    def __init__(self, parent):
        self.parent = parent
        self.active = False
        self.timer = None
        self.start_time = None
        self.end_time = None
        self.current_preset = None
        self.original_websites = {}
        self.original_apps = {}
        
    def start(self, preset_name):
        if preset_name not in FOCUS_MODE_PRESETS:
            return False
            
        self.current_preset = FOCUS_MODE_PRESETS[preset_name]
        self.active = True
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(minutes=self.current_preset["duration"])
        
        # 备份当前设置
        self.original_websites = self.parent.websites.copy()
        self.original_apps = self.parent.blocked_apps.copy()
        
        # 应用专注模式设置
        if self.current_preset["block_social"]:
            self._add_category_websites("社交媒体")
            self._add_category_websites("在线聊天")
            
        if self.current_preset["block_entertainment"]:
            self._add_category_websites("视频娱乐")
            self._add_category_websites("游戏平台")
            
        if self.current_preset["block_shopping"]:
            self._add_category_websites("购物网站")
            
        if self.current_preset["block_apps"]:
            self._block_apps()
            
        # 启动定时器
        self.timer = threading.Timer(
            self.current_preset["duration"] * 60,
            self.stop
        )
        self.timer.start()
        
        return True
        
    def stop(self):
        if not self.active:
            return
            
        self.active = False
        if self.timer:
            self.timer.cancel()
            
        # 恢复原始设置
        self.parent.websites = self.original_websites.copy()
        self.parent.blocked_apps = self.original_apps.copy()
        
        # 更新hosts文件
        self.parent.modify_hosts()
        
    def _add_category_websites(self, category):
        if category in PRESET_WEBSITES:
            if "专注模式" not in self.parent.websites:
                self.parent.websites["专注模式"] = []
            self.parent.websites["专注模式"].extend(PRESET_WEBSITES[category])
            
    def _block_apps(self):
        for category, apps in DEFAULT_APP_BLACKLIST.items():
            self.parent.blocked_apps.extend(apps)
            
    def get_remaining_time(self):
        if not self.active or not self.end_time:
            return None
        remaining = self.end_time - datetime.now()
        return max(remaining.total_seconds(), 0)
        
class AppBlocker:
    def __init__(self):
        self.blocked_apps = []
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_apps)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
            
    def _monitor_apps(self):
        while self.monitoring:
            try:
                active_window = GetForegroundWindow()
                window_title = GetWindowText(active_window)
                
                for proc in psutil.process_iter(['name', 'pid']):
                    if proc.info['name'].lower() in [app.lower() for app in self.blocked_apps]:
                        try:
                            proc.terminate()
                        except:
                            pass
                            
                time.sleep(1)
            except:
                continue
                
class CloudSync:
    def __init__(self, parent):
        self.parent = parent
        
    def backup_to_cloud(self):
        try:
            config = {
                "websites": self.parent.websites,
                "block_times": self.parent.block_times,
                "whitelist": self.parent.whitelist,
                "force_mode": self.parent.force_mode,
                "silent_mode": self.parent.silent_mode,
                "stats": self.parent.stats
            }
            
            response = requests.post(
                CLOUD_BACKUP_URL,
                json=config,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return True, "云端备份成功"
            return False, f"云端备份失败: {response.text}"
            
        except Exception as e:
            return False, f"云端备份失败: {str(e)}"
            
    def restore_from_cloud(self):
        try:
            response = requests.get(CLOUD_BACKUP_URL)
            
            if response.status_code == 200:
                config = response.json()
                self.parent.websites = config.get("websites", {})
                self.parent.block_times = config.get("block_times", {})
                self.parent.whitelist = config.get("whitelist", [])
                self.parent.force_mode = config.get("force_mode", False)
                self.parent.silent_mode = config.get("silent_mode", False)
                self.parent.stats = config.get("stats", {})
                return True, "从云端恢复成功"
            return False, f"从云端恢复失败: {response.text}"
            
        except Exception as e:
            return False, f"从云端恢复失败: {str(e)}"
            
class WebsiteRecommender:
    def __init__(self, parent):
        self.parent = parent
        self.visit_history = {}
        
    def track_visit(self, website):
        if website not in self.visit_history:
            self.visit_history[website] = {
                "visit_count": 0,
                "last_visit": None
            }
            
        self.visit_history[website]["visit_count"] += 1
        self.visit_history[website]["last_visit"] = datetime.now()
        
    def get_recommendations(self):
        recommendations = []
        
        # 根据访问频率推荐
        frequent_sites = sorted(
            self.visit_history.items(),
            key=lambda x: x[1]["visit_count"],
            reverse=True
        )
        
        for site, data in frequent_sites[:5]:
            if not self._is_blocked(site):
                recommendations.append({
                    "website": site,
                    "reason": f"频繁访问 ({data['visit_count']} 次)",
                    "score": data["visit_count"]
                })
                
        return recommendations
        
    def _is_blocked(self, website):
        return any(website in sites for sites in self.parent.websites.values())

class TimeUnlocker:
    def __init__(self, parent):
        self.parent = parent
        self.unlock_times = {}
        
    def add_unlock_time(self, website, duration_minutes):
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        self.unlock_times[website] = end_time
        
    def is_unlocked(self, website):
        if website not in self.unlock_times:
            return False
            
        if datetime.now() > self.unlock_times[website]:
            del self.unlock_times[website]
            return False
            
        return True
        
    def get_remaining_time(self, website):
        if website not in self.unlock_times:
            return 0
            
        remaining = self.unlock_times[website] - datetime.now()
        return max(remaining.total_seconds() / 60, 0)  # 返回剩余分钟数

class GlobalHotkeys:
    def __init__(self, parent):
        self.parent = parent
        self.registered = False
        
    def register(self):
        if self.registered:
            return
            
        try:
            for action, hotkey in DEFAULT_SHORTCUTS.items():
                keyboard.add_hotkey(hotkey, self._create_callback(action))
            self.registered = True
            return True
        except Exception as e:
            logging.error(f"注册快捷键失败: {str(e)}")
            return False
            
    def unregister(self):
        if not self.registered:
            return
            
        try:
            keyboard.unhook_all()
            self.registered = False
            return True
        except Exception as e:
            logging.error(f"注销快捷键失败: {str(e)}")
            return False
            
    def _create_callback(self, action):
        callbacks = {
            "toggle_block": lambda: self.parent._toggle_pause(),
            "focus_mode": lambda: self.parent._show_focus_mode(),
            "quick_unlock": lambda: self.parent._show_quick_unlock(),
            "show_stats": lambda: self.parent._show_stats(),
            "add_website": lambda: self.parent._show_add_website()
        }
        return callbacks.get(action, lambda: None)

def check_autostart():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_PATH,
            0,
            winreg.KEY_READ
        )
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except:
        return False

def set_autostart(enable):
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_PATH,
            0,
            winreg.KEY_WRITE
        )
        
        if enable:
            # 获取当前程序路径
            if getattr(sys, 'frozen', False):
                app_path = sys.executable
            else:
                app_path = os.path.abspath(__file__)
                
            winreg.SetValueEx(
                key,
                APP_NAME,
                0,
                winreg.REG_SZ,
                f'"{app_path}"'
            )
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except:
                pass
                
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logging.error(f"设置开机自启动失败: {str(e)}")
        return False

class FocusModeWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.title("专注模式")
        self.geometry("600x800")
        self.minsize(600, 800)
        
        # 设置主题
        self.configure(fg_color=THEME_COLORS["background"])
        
        # 标题
        title = ctk.CTkLabel(
            self,
            text="专注模式",
            font=("Microsoft YaHei UI", 24, "bold"),
            text_color=THEME_COLORS["text"]
        )
        title.pack(pady=20)
        
        # 主容器
        main_frame = ctk.CTkFrame(
            self,
            fg_color=THEME_COLORS["surface"],
            corner_radius=20,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        main_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        
        # 模式选择区域
        mode_frame = ctk.CTkFrame(
            main_frame,
            fg_color=THEME_COLORS["background"],
            corner_radius=15,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        mode_frame.pack(fill="x", padx=20, pady=15)
        
        mode_label = ctk.CTkLabel(
            mode_frame,
            text="选择专注模式",
            font=("Microsoft YaHei UI", 16, "bold"),
            text_color=THEME_COLORS["text"]
        )
        mode_label.pack(pady=10)
        
        # 创建模式按钮
        for preset_name, preset in FOCUS_MODE_PRESETS.items():
            mode_btn = ctk.CTkButton(
                mode_frame,
                text=f"{preset_name} ({preset['duration']}分钟)",
                command=lambda name=preset_name: self._start_focus_mode(name),
                width=250,
                height=40,
                font=("Microsoft YaHei UI", 14),
                fg_color=THEME_COLORS["primary"],
                hover_color=THEME_COLORS["primary_hover"],
                corner_radius=8
            )
            mode_btn.pack(pady=5)
            
        # 自定义设置区域
        custom_frame = ctk.CTkFrame(
            main_frame,
            fg_color=THEME_COLORS["background"],
            corner_radius=15,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        custom_frame.pack(fill="x", padx=20, pady=15)
        
        custom_label = ctk.CTkLabel(
            custom_frame,
            text="自定义设置",
            font=("Microsoft YaHei UI", 16, "bold"),
            text_color=THEME_COLORS["text"]
        )
        custom_label.pack(pady=10)
        
        # 时长设置
        duration_frame = ctk.CTkFrame(custom_frame, fg_color="transparent")
        duration_frame.pack(pady=5)
        
        ctk.CTkLabel(
            duration_frame,
            text="专注时长(分钟):",
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"]
        ).pack(side="left", padx=5)
        
        self.duration_entry = ctk.CTkEntry(
            duration_frame,
            width=100,
            height=30,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["secondary"],
            border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text"]
        )
        self.duration_entry.pack(side="left", padx=5)
        self.duration_entry.insert(0, "25")
        
        # 屏蔽选项
        options_frame = ctk.CTkFrame(
            custom_frame,
            fg_color="transparent"
        )
        options_frame.pack(pady=10)
        
        self.block_social_var = tk.BooleanVar(value=True)
        social_switch = ctk.CTkSwitch(
            options_frame,
            text="屏蔽社交网站",
            variable=self.block_social_var,
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"],
            progress_color=THEME_COLORS["primary"],
            button_color=THEME_COLORS["primary"],
            button_hover_color=THEME_COLORS["primary_hover"]
        )
        social_switch.pack(pady=5)
        
        self.block_entertainment_var = tk.BooleanVar(value=True)
        entertainment_switch = ctk.CTkSwitch(
            options_frame,
            text="屏蔽娱乐网站",
            variable=self.block_entertainment_var,
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"],
            progress_color=THEME_COLORS["primary"],
            button_color=THEME_COLORS["primary"],
            button_hover_color=THEME_COLORS["primary_hover"]
        )
        entertainment_switch.pack(pady=5)
        
        self.block_shopping_var = tk.BooleanVar(value=True)
        shopping_switch = ctk.CTkSwitch(
            options_frame,
            text="屏蔽购物网站",
            variable=self.block_shopping_var,
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"],
            progress_color=THEME_COLORS["primary"],
            button_color=THEME_COLORS["primary"],
            button_hover_color=THEME_COLORS["primary_hover"]
        )
        shopping_switch.pack(pady=5)
        
        self.block_apps_var = tk.BooleanVar(value=True)
        apps_switch = ctk.CTkSwitch(
            options_frame,
            text="屏蔽应用程序",
            variable=self.block_apps_var,
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"],
            progress_color=THEME_COLORS["primary"],
            button_color=THEME_COLORS["primary"],
            button_hover_color=THEME_COLORS["primary_hover"]
        )
        apps_switch.pack(pady=5)
        
        # 开始按钮
        start_btn = ctk.CTkButton(
            custom_frame,
            text="开始专注",
            command=self._start_custom_focus,
            width=250,
            height=40,
            font=("Microsoft YaHei UI", 14),
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS["primary_hover"],
            corner_radius=8
        )
        start_btn.pack(pady=15)
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"]
        )
        self.status_label.pack(pady=10)
        
        # 使窗口模态
        self.transient(parent)
        self.grab_set()
        
    def _start_focus_mode(self, preset_name):
        if self.parent.focus_mode.start(preset_name):
            self.status_label.configure(text=f"已启动{preset_name}")
            self.after(2000, self.destroy)
        else:
            self.status_label.configure(text="启动专注模式失败")
            
    def _start_custom_focus(self):
        try:
            duration = int(self.duration_entry.get())
            if duration <= 0:
                raise ValueError()
                
            custom_preset = {
                "duration": duration,
                "break_time": 5,
                "block_social": self.block_social_var.get(),
                "block_entertainment": self.block_entertainment_var.get(),
                "block_shopping": self.block_shopping_var.get(),
                "block_apps": self.block_apps_var.get()
            }
            
            FOCUS_MODE_PRESETS["自定义"] = custom_preset
            if self.parent.focus_mode.start("自定义"):
                self.status_label.configure(text="已启动自定义专注模式")
                self.after(2000, self.destroy)
            else:
                self.status_label.configure(text="启动专注模式失败")
                
        except ValueError:
            self.status_label.configure(text="请输入有效的时长")

class QuickUnlockWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.title("快速解锁")
        self.geometry("500x600")
        self.minsize(500, 600)
        
        # 设置主题
        self.configure(fg_color=THEME_COLORS["background"])
        
        # 标题
        title = ctk.CTkLabel(
            self,
            text="快速解锁",
            font=("Microsoft YaHei UI", 24, "bold"),
            text_color=THEME_COLORS["text"]
        )
        title.pack(pady=20)
        
        # 主容器
        main_frame = ctk.CTkFrame(
            self,
            fg_color=THEME_COLORS["surface"],
            corner_radius=20,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        main_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        
        # 网站选择区域
        website_frame = ctk.CTkFrame(
            main_frame,
            fg_color=THEME_COLORS["background"],
            corner_radius=15,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        website_frame.pack(fill="x", padx=20, pady=15)
        
        website_label = ctk.CTkLabel(
            website_frame,
            text="选择网站",
            font=("Microsoft YaHei UI", 16, "bold"),
            text_color=THEME_COLORS["text"]
        )
        website_label.pack(pady=10)
        
        # 创建网站列表
        self.website_list = tk.Listbox(
            website_frame,
            selectmode="single",
            font=("Microsoft YaHei UI", 12),
            bg=THEME_COLORS["background"],
            fg=THEME_COLORS["text"],
            selectbackground=THEME_COLORS["primary"],
            selectforeground=THEME_COLORS["text"],
            borderwidth=0,
            highlightthickness=0
        )
        self.website_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 更新网站列表
        self._update_website_list()
        
        # 时长设置
        duration_frame = ctk.CTkFrame(
            main_frame,
            fg_color=THEME_COLORS["background"],
            corner_radius=15,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        duration_frame.pack(fill="x", padx=20, pady=15)
        
        duration_label = ctk.CTkLabel(
            duration_frame,
            text="解锁时长(分钟)",
            font=("Microsoft YaHei UI", 16, "bold"),
            text_color=THEME_COLORS["text"]
        )
        duration_label.pack(pady=10)
        
        self.duration_entry = ctk.CTkEntry(
            duration_frame,
            width=200,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["secondary"],
            border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text"]
        )
        self.duration_entry.pack(pady=5)
        self.duration_entry.insert(0, "30")
        
        # 解锁按钮
        unlock_btn = ctk.CTkButton(
            main_frame,
            text="解锁",
            command=self._unlock,
            width=250,
            height=40,
            font=("Microsoft YaHei UI", 14),
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS["primary_hover"],
            corner_radius=8
        )
        unlock_btn.pack(pady=20)
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"]
        )
        self.status_label.pack(pady=10)
        
        # 使窗口模态
        self.transient(parent)
        self.grab_set()
        
    def _update_website_list(self):
        self.website_list.delete(0, tk.END)
        for group, sites in self.parent.websites.items():
            for site in sites:
                self.website_list.insert(tk.END, f"{site} ({group})")
                
    def _unlock(self):
        selection = self.website_list.curselection()
        if not selection:
            self.status_label.configure(text="请选择要解锁的网站")
            return
            
        try:
            duration = int(self.duration_entry.get())
            if duration <= 0:
                raise ValueError()
                
            website = self.website_list.get(selection[0]).split(" (")[0]
            self.parent.time_unlocker.add_unlock_time(website, duration)
            self.status_label.configure(text=f"已解锁 {website} {duration}分钟")
            self.after(2000, self.destroy)
            
        except ValueError:
            self.status_label.configure(text="请输入有效的时长")

class RecommendWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.title("网站推荐")
        self.geometry("600x700")
        self.minsize(600, 700)
        
        # 设置主题
        self.configure(fg_color=THEME_COLORS["background"])
        
        # 标题
        title = ctk.CTkLabel(
            self,
            text="推荐屏蔽的网站",
            font=("Microsoft YaHei UI", 24, "bold"),
            text_color=THEME_COLORS["text"]
        )
        title.pack(pady=20)
        
        # 主容器
        main_frame = ctk.CTkFrame(
            self,
            fg_color=THEME_COLORS["surface"],
            corner_radius=20,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        main_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        
        # 推荐列表区域
        recommend_frame = ctk.CTkFrame(
            main_frame,
            fg_color=THEME_COLORS["background"],
            corner_radius=15,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        recommend_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        # 获取推荐
        recommendations = self.parent.recommender.get_recommendations()
        
        if not recommendations:
            no_data_label = ctk.CTkLabel(
                recommend_frame,
                text="暂无推荐数据",
                font=("Microsoft YaHei UI", 14),
                text_color=THEME_COLORS["text_secondary"]
            )
            no_data_label.pack(pady=20)
        else:
            for rec in recommendations:
                site_frame = ctk.CTkFrame(
                    recommend_frame,
                    fg_color=THEME_COLORS["surface"],
                    corner_radius=8
                )
                site_frame.pack(fill="x", padx=10, pady=5)
                
                site_label = ctk.CTkLabel(
                    site_frame,
                    text=rec["website"],
                    font=("Microsoft YaHei UI", 14),
                    text_color=THEME_COLORS["text"]
                )
                site_label.pack(side="left", padx=10, pady=10)
                
                reason_label = ctk.CTkLabel(
                    site_frame,
                    text=rec["reason"],
                    font=("Microsoft YaHei UI", 12),
                    text_color=THEME_COLORS["text_secondary"]
                )
                reason_label.pack(side="left", padx=10, pady=10)
                
                add_btn = ctk.CTkButton(
                    site_frame,
                    text="添加",
                    command=lambda w=rec["website"]: self._add_website(w),
                    width=100,
                    height=30,
                    font=("Microsoft YaHei UI", 12),
                    fg_color=THEME_COLORS["primary"],
                    hover_color=THEME_COLORS["primary_hover"],
                    corner_radius=8
                )
                add_btn.pack(side="right", padx=10, pady=10)
                
        # 状态标签
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"]
        )
        self.status_label.pack(pady=10)
        
        # 使窗口模态
        self.transient(parent)
        self.grab_set()
        
    def _add_website(self, website):
        if "推荐" not in self.parent.websites:
            self.parent.websites["推荐"] = []
            
        if website not in self.parent.websites["推荐"]:
            self.parent.websites["推荐"].append(website)
            self.parent._save_config()
            self.status_label.configure(text=f"已添加 {website}")
        else:
            self.status_label.configure(text="该网站已存在")

class AppBlockerWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.title("应用程序屏蔽")
        self.geometry("800x600")
        self.minsize(800, 600)
        
        # 设置主题
        self.configure(fg_color=THEME_COLORS["background"])
        
        # 标题
        title = ctk.CTkLabel(
            self,
            text="应用程序屏蔽",
            font=("Microsoft YaHei UI", 24, "bold"),
            text_color=THEME_COLORS["text"]
        )
        title.pack(pady=20)
        
        # 主容器
        main_frame = ctk.CTkFrame(
            self,
            fg_color=THEME_COLORS["surface"],
            corner_radius=20,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        main_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        
        # 应用程序列表区域
        app_frame = ctk.CTkFrame(
            main_frame,
            fg_color=THEME_COLORS["background"],
            corner_radius=15,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        app_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        # 分类选择
        category_frame = ctk.CTkFrame(
            app_frame,
            fg_color="transparent"
        )
        category_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            category_frame,
            text="选择分类:",
            font=("Microsoft YaHei UI", 14),
            text_color=THEME_COLORS["text"]
        ).pack(side="left", padx=5)
        
        self.category_var = tk.StringVar(value=list(DEFAULT_APP_BLACKLIST.keys())[0])
        category_menu = ctk.CTkOptionMenu(
            category_frame,
            values=list(DEFAULT_APP_BLACKLIST.keys()),
            variable=self.category_var,
            command=self._on_category_change,
            width=150,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["secondary"],
            button_color=THEME_COLORS["primary"],
            button_hover_color=THEME_COLORS["primary_hover"]
        )
        category_menu.pack(side="left", padx=5)
        
        # 应用程序列表
        list_frame = ctk.CTkFrame(
            app_frame,
            fg_color=THEME_COLORS["surface"],
            corner_radius=8,
            border_width=1,
            border_color=THEME_COLORS["border"]
        )
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 创建应用程序列表
        self.app_list = tk.Listbox(
            list_frame,
            selectmode="multiple",
            font=("Microsoft YaHei UI", 12),
            bg=THEME_COLORS["background"],
            fg=THEME_COLORS["text"],
            selectbackground=THEME_COLORS["primary"],
            selectforeground=THEME_COLORS["text"],
            borderwidth=0,
            highlightthickness=0
        )
        self.app_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 按钮区域
        button_frame = ctk.CTkFrame(
            app_frame,
            fg_color="transparent"
        )
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 添加应用按钮
        add_btn = ctk.CTkButton(
            button_frame,
            text="添加应用",
            command=self._add_app,
            width=150,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS["primary_hover"],
            corner_radius=8
        )
        add_btn.pack(side="left", padx=5)
        
        # 删除应用按钮
        delete_btn = ctk.CTkButton(
            button_frame,
            text="删除选中",
            command=self._delete_app,
            width=150,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["error"],
            hover_color="#A32929",
            corner_radius=8
        )
        delete_btn.pack(side="left", padx=5)
        
        # 刷新列表按钮
        refresh_btn = ctk.CTkButton(
            button_frame,
            text="刷新列表",
            command=self._refresh_list,
            width=150,
            height=35,
            font=("Microsoft YaHei UI", 12),
            fg_color=THEME_COLORS["primary"],
            hover_color=THEME_COLORS["primary_hover"],
            corner_radius=8
        )
        refresh_btn.pack(side="right", padx=5)
        
        # 状态标签
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=("Microsoft YaHei UI", 12),
            text_color=THEME_COLORS["text_secondary"]
        )
        self.status_label.pack(pady=10)
        
        # 更新列表
        self._refresh_list()
        
        # 使窗口模态
        self.transient(parent)
        self.grab_set()
        
    def _on_category_change(self, choice):
        self._refresh_list()
        
    def _refresh_list(self):
        self.app_list.delete(0, tk.END)
        category = self.category_var.get()
        
        # 添加预设应用
        if category in DEFAULT_APP_BLACKLIST:
            for app in DEFAULT_APP_BLACKLIST[category]:
                if app in self.parent.blocked_apps:
                    self.app_list.insert(tk.END, f"✓ {app}")
                else:
                    self.app_list.insert(tk.END, app)
                    
        # 添加当前运行的应用
        running_apps = set()
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name'].lower()
                if name.endswith('.exe'):
                    running_apps.add(name)
            except:
                continue
                
        for app in sorted(running_apps):
            if app not in DEFAULT_APP_BLACKLIST.get(category, []):
                if app in self.parent.blocked_apps:
                    self.app_list.insert(tk.END, f"✓ {app}")
                else:
                    self.app_list.insert(tk.END, app)
                    
    def _add_app(self):
        selection = self.app_list.curselection()
        if not selection:
            self.status_label.configure(text="请选择要屏蔽的应用")
            return
            
        added = 0
        for index in selection:
            app = self.app_list.get(index).replace("✓ ", "")
            if app not in self.parent.blocked_apps:
                self.parent.blocked_apps.append(app)
                added += 1
                
        if added > 0:
            self.parent._save_config()
            self._refresh_list()
            self.status_label.configure(text=f"已添加 {added} 个应用")
        else:
            self.status_label.configure(text="选中的应用已在屏蔽列表中")
            
    def _delete_app(self):
        selection = self.app_list.curselection()
        if not selection:
            self.status_label.configure(text="请选择要解除屏蔽的应用")
            return
            
        removed = 0
        for index in selection:
            app = self.app_list.get(index).replace("✓ ", "")
            if app in self.parent.blocked_apps:
                self.parent.blocked_apps.remove(app)
                removed += 1
                
        if removed > 0:
            self.parent._save_config()
            self._refresh_list()
            self.status_label.configure(text=f"已移除 {removed} 个应用")
        else:
            self.status_label.configure(text="选中的应用不在屏蔽列表中")

if __name__ == "__main__":
    app = WebsiteBlocker()
    app.run() 