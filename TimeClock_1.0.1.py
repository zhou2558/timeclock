#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TimeClock v1.0.1
定时提醒程序 - 浅色风格 + Windows原生通知
参照"提醒助手"UI设计 - 最终优化版
"""

import customtkinter as ctk
import json
import os
import sys
import ctypes
import threading
from datetime import datetime, timedelta
from threading import Timer
from windows_toasts import WindowsToaster, Toast, ToastDisplayImage, ToastImagePosition
from pystray import MenuItem as item
import pystray
from PIL import Image, ImageDraw, ImageFont
from customtkinter import CTkImage
import winreg

# ==================== 全局字体配置(统一字体)====================
FONT_FAMILY = "Microsoft YaHei UI"  # Windows 系统中文字体

def F(size=13, weight="normal"):
    """快速创建字体"""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)

# ==================== 配置 ====================
APP_NAME = "提醒助手"
APP_VERSION = "1.0.1"

# 资源目录:打包后(单文件夹)资源放在 _internal 内,开发直接运行 .py 时回退到脚本同目录
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_INTERNAL_DIR = os.path.join(_BASE_DIR, "_internal")
_RES_DIR = _INTERNAL_DIR if os.path.isdir(_INTERNAL_DIR) else _BASE_DIR

DATA_FILE = os.path.join(_RES_DIR, "data.json")
ICON_PATH = os.path.join(_RES_DIR, "time.ico")

# ==================== 颜色配置(严格按用户要求)====================
# 新建提醒按钮(主操作,实心蓝)
COLOR_NEW_BG = "#2B7AEC"
COLOR_NEW_TEXT = "#FFFFFF"
COLOR_NEW_HOVER = "#1E5FBF"

# 编辑按钮(次要操作,淑蓝背景)
COLOR_EDIT_BG = "#E3F1FC"
COLOR_EDIT_TEXT = "#42597E"
COLOR_EDIT_HOVER = "#D6E9F7"

# 删除按钮(警示操作,淑粉背景)
COLOR_DELETE_BG = "#FDE5E2"
COLOR_DELETE_TEXT = "#BC5C63"
COLOR_DELETE_HOVER = "#FBD5D0"

# 其他配色
COLOR_BG = "#F5F7FA"
COLOR_CARD = "#FFFFFF"
COLOR_CARD_BORDER = "#E5E7EB"
COLOR_TEXT_PRIMARY = "#1F2937"
COLOR_TEXT_SECONDARY = "#6B7280"
COLOR_TEXT_TERTIARY = "#9CA3AF"

COLOR_BADGE_DISABLED_BG = "#F3F4F6"
COLOR_BADGE_DISABLED_TEXT = "#9CA3AF"
COLOR_BADGE_COUNTDOWN_BG = "#DCFCE7"
COLOR_BADGE_COUNTDOWN_TEXT = "#15803D"

COLOR_TYPE_SCHEDULED = "#3B82F6"
COLOR_TYPE_COUNTDOWN = "#10B981"
COLOR_TYPE_LOOP = "#8B5CF6"

COLOR_ICON_BG_BLUE = "#DBEAFE"
COLOR_ICON_BG_GREEN = "#D1FAE5"
COLOR_ICON_BG_PURPLE = "#EDE9FE"

# 卡片背景色(基于图标背景色,浅色、近白)
COLOR_CARD_SCHEDULED = "#EFF6FF"   # 蓝:#DBEAFE 浅化
COLOR_CARD_COUNTDOWN = "#ECFDF5"   # 绿:#D1FAE5 浅化
COLOR_CARD_LOOP = "#F5F3FF"        # 紫:#EDE9FE 浅化
COLOR_CARD_BG_MAP = {
    "scheduled": COLOR_CARD_SCHEDULED,
    "countdown": COLOR_CARD_COUNTDOWN,
    "loop": COLOR_CARD_LOOP,
}

# ==================== iOS 风格开关 ====================
class IOSSwitch(ctk.CTkFrame):
    """自定义 iOS 风格开关:白色圆形手柄,清晰可见"""
    def __init__(self, master, command=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.command = command
        self._is_on = False

        # 尺寸配置(高度与按钮一致 32)
        self.track_width = 76
        self.track_height = 32
        self.handle_size = 24   # 圆形手柄,略小于轨道高度
        self.padding = 4         # 手柄距轨道边缘距离

        self.configure(width=self.track_width, height=self.track_height)
        self.pack_propagate(False)

        # 轨道
        self.track = ctk.CTkFrame(
            self, width=self.track_width, height=self.track_height,
            fg_color="#94A3B8", corner_radius=self.track_height // 2
        )
        self.track.place(x=0, y=0)

        # 白色圆形手柄
        self.handle = ctk.CTkLabel(
            self, text="",
            width=self.handle_size, height=self.handle_size,
            fg_color="white", corner_radius=self.handle_size // 2
        )
        self.handle.place(x=self.padding, y=self.padding)

        # 绑定点击事件
        for widget in [self, self.track, self.handle]:
            widget.bind("<Button-1>", self._toggle)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event=None):
        self.configure(cursor="hand2")

    def _on_leave(self, event=None):
        self.configure(cursor="")

    def _toggle(self, event=None):
        self._is_on = not self._is_on
        self._update_visual()
        if self.command:
            self.command()

    def _update_visual(self):
        if self._is_on:
            self.track.configure(fg_color="#3B82F6")  # 开启:蓝色
            x = self.track_width - self.handle_size - self.padding
        else:
            self.track.configure(fg_color="#94A3B8")  # 关闭:深灰
            x = self.padding
        self.handle.place(x=x, y=self.padding)

    def get(self):
        return self._is_on

    def set(self, value):
        self._is_on = bool(value)
        self._update_visual()

# ==================== 图标生成器 ====================
class IconGenerator:
    """使用PIL绘制清晰的图标(不依赖emoji字体)"""

    @staticmethod
    def draw_clock_icon(draw, size, color):
        """绘制时钟图标"""
        center = size // 2
        radius = size // 3
        # 圆环
        draw.ellipse([center-radius, center-radius, center+radius, center+radius],
                     outline=color, width=max(2, size//20))
        # 时针
        draw.line([center, center, center, center-radius//2],
                  fill=color, width=max(2, size//25))
        # 分针
        draw.line([center, center, center+radius*2//3, center],
                  fill=color, width=max(2, size//25))
        # 中心点
        r = max(2, size//40)
        draw.ellipse([center-r, center-r, center+r, center+r], fill=color)

    @staticmethod
    def draw_loop_icon(draw, size, color):
        """绘制循环图标(环形箭头)"""
        center = size // 2
        radius = size // 3
        w = max(2, size//20)
        # 上半圆弧
        draw.arc([center-radius, center-radius, center+radius, center+radius],
                 start=30, end=330, fill=color, width=w)
        # 箭头
        arrow_size = size // 10
        draw.polygon([
            (center + radius - arrow_size//2, center - radius + arrow_size),
            (center + radius + arrow_size, center - radius + arrow_size//2),
            (center + radius - arrow_size//2, center - radius - arrow_size//2)
        ], fill=color)

    @staticmethod
    def draw_gear_icon(draw, size, color):
        """绘制齿轮图标"""
        center = size // 2
        outer_r = size // 3
        inner_r = size // 5
        w = max(2, size//20)
        # 简化版齿轮 - 圆环
        draw.ellipse([center-outer_r, center-outer_r, center+outer_r, center+outer_r],
                     outline=color, width=w)
        draw.ellipse([center-inner_r, center-inner_r, center+inner_r, center+inner_r],
                     outline=color, width=w)
        # 4个齿
        for angle in [0, 90, 180, 270]:
            import math
            rad = math.radians(angle)
            x1 = center + int(outer_r * math.cos(rad))
            y1 = center + int(outer_r * math.sin(rad))
            x2 = center + int((outer_r + size//15) * math.cos(rad))
            y2 = center + int((outer_r + size//15) * math.sin(rad))
            draw.line([x1, y1, x2, y2], fill=color, width=w)

    @staticmethod
    def create_icon(icon_type, size=80):
        """创建彩色背景图标"""
        try:
            # 背景颜色和图标颜色
            configs = {
                "scheduled": (COLOR_ICON_BG_BLUE, "#3B82F6"),
                "countdown": (COLOR_ICON_BG_GREEN, "#10B981"),
                "loop": (COLOR_ICON_BG_PURPLE, "#8B5CF6"),
                "logo": (COLOR_ICON_BG_BLUE, "#3B82F6"),
                "gear": ("#DBEAFE", "#3B82F6")
            }
            bg_color, fg_color = configs.get(icon_type, configs["scheduled"])

            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 圆角矩形背景
            radius = size // 5
            draw.rounded_rectangle([(0, 0), (size, size)], radius=radius, fill=bg_color)

            # 绘制对应图标
            if icon_type in ["scheduled", "countdown", "logo"]:
                IconGenerator.draw_clock_icon(draw, size, fg_color)
            elif icon_type == "loop":
                IconGenerator.draw_loop_icon(draw, size, fg_color)
            elif icon_type == "gear":
                IconGenerator.draw_gear_icon(draw, size, fg_color)

            return img
        except Exception as e:
            print(f"创建图标失败: {e}")
            return None

# ==================== 通知管理器 ====================
class NotificationManager:
    def __init__(self):
        try:
            self.toaster = WindowsToaster("TimeClock")
        except Exception as e:
            print(f"通知初始化失败: {e}")
            self.toaster = None

    def send_notification(self, title, message):
        """发送Windows原生通知(无弹窗,无按钮)"""
        try:
            if self.toaster is None:
                print(f"[通知] {title}: {message}")
                return
            new_toast = Toast()
            new_toast.text_fields = [title, message]
            # 通知图标:使用 time.ico(打包后位于 _internal,开发时回退脚本同目录)
            try:
                if os.path.exists(ICON_PATH):
                    new_toast.AddImage(
                        ToastDisplayImage.fromPath(
                            ICON_PATH,
                            altText=APP_NAME,
                            position=ToastImagePosition.AppLogo,
                        )
                    )
            except Exception as e:
                print(f"设置通知图标失败(不影响通知): {e}")
            self.toaster.show_toast(new_toast)
        except Exception as e:
            print(f"发送通知失败: {e}")

# ==================== 提醒类 ====================
class Reminder:
    def __init__(self, reminder_id, reminder_type, hour, minute, second, title, content, enabled=True):
        self.id = reminder_id
        self.type = reminder_type
        self.hour = hour
        self.minute = minute
        self.second = second
        self.title = title
        self.content = content
        self.enabled = enabled
        self.timer = None
        self.next_trigger = None
        self.calculate_next_trigger()

    def calculate_next_trigger(self):
        now = datetime.now()
        if self.type == "scheduled":
            trigger_time = now.replace(hour=self.hour, minute=self.minute, second=self.second, microsecond=0)
            if trigger_time <= now:
                trigger_time += timedelta(days=1)
            self.next_trigger = trigger_time
        elif self.type == "countdown":
            delta = timedelta(hours=self.hour, minutes=self.minute, seconds=self.second)
            self.next_trigger = now + delta
        elif self.type == "loop":
            delta = timedelta(hours=self.hour, minutes=self.minute, seconds=self.second)
            self.next_trigger = now + delta

    def get_remaining_seconds(self):
        if not self.next_trigger:
            return 0
        delta = (self.next_trigger - datetime.now()).total_seconds()
        return max(0, int(delta))

    def format_remaining_time(self):
        seconds = self.get_remaining_seconds()
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def start(self, callback):
        if not self.enabled:
            return
        self.stop()
        now = datetime.now()
        if self.next_trigger and self.next_trigger > now:
            delta = (self.next_trigger - now).total_seconds()
            self.timer = Timer(delta, self._trigger, args=[callback])
            self.timer.daemon = True
            self.timer.start()

    def _trigger(self, callback):
        if self.enabled:
            callback(self)
            self.calculate_next_trigger()
            self.start(callback)

    def stop(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def to_dict(self):
        return {"id": self.id, "type": self.type, "hour": self.hour,
                "minute": self.minute, "second": self.second,
                "title": self.title, "content": self.content, "enabled": self.enabled}

    @staticmethod
    def from_dict(data):
        return Reminder(data["id"], data["type"], data["hour"],
                       data["minute"], data["second"],
                       data["title"], data["content"], data["enabled"])

# ==================== 数据管理器 ====================
class DataManager:
    def __init__(self, filename):
        self.filename = filename
        self.reminders = []
        self.load()

    def load(self):
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.reminders = [Reminder.from_dict(r) for r in data]
        except Exception as e:
            print(f"加载数据失败: {e}")
            self.reminders = []

    def save(self):
        """保存数据到 JSON 文件,使用重试机制避免 Windows 文件锁定问题"""
        import time
        max_retries = 5
        for attempt in range(max_retries):
            try:
                data = [r.to_dict() for r in self.reminders]
                with open(self.filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return  # 成功
            except PermissionError as e:
                if attempt < max_retries - 1:
                    time.sleep(0.2)  # 等待 200ms 后重试
                else:
                    print(f"保存数据失败: {e}")
            except Exception as e:
                print(f"保存数据失败: {e}")
                return

    def add_reminder(self, reminder):
        self.reminders.append(reminder)
        self.save()

    def remove_reminder(self, reminder_id):
        self.reminders = [r for r in self.reminders if r.id != reminder_id]
        self.save()

    def update_reminder(self, reminder):
        for i, r in enumerate(self.reminders):
            if r.id == reminder.id:
                self.reminders[i] = reminder
                break
        self.save()

# ==================== 开机自启管理器 ====================
class StartupManager:
    def __init__(self, app_name):
        self.app_name = app_name
        self.reg_key = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def is_startup_enabled(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_key, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, self.app_name)
            winreg.CloseKey(key)
            return True
        except:
            return False

    def enable_startup(self):
        try:
            python_path = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(python_path):
                python_path = sys.executable
            exe_path = os.path.abspath(sys.argv[0])
            command = f'"{python_path}" "{exe_path}"'
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_key, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"启用开机自启失败: {e}")
            return False

    def disable_startup(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_key, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, self.app_name)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"禁用开机自启失败: {e}")
            return False

# ==================== 系统托盘管理器 ====================
class TrayManager:
    def __init__(self, app):
        self.app = app
        self.icon = None

    def load_icon_image(self):
        try:
            if os.path.exists(ICON_PATH):
                img = Image.open(ICON_PATH)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                img = img.resize((64, 64), Image.Resampling.LANCZOS)
                return img
        except:
            pass
        return IconGenerator.create_icon("logo", 64)

    def setup(self):
        menu = pystray.Menu(
            item('显示窗口', self.show_window, default=True),
            item('退出', self.quit_app)
        )
        self.icon = pystray.Icon(APP_NAME, self.load_icon_image(), APP_NAME, menu)

    def show_window(self):
        self.app.show_window()

    def quit_app(self):
        self.app.quit_app()

    def run(self):
        self.setup()
        self.icon.run()

# ==================== 主应用程序 ====================
class TimeClockApp:
    def __init__(self):
        self.data_manager = DataManager(DATA_FILE)
        self.notification_manager = NotificationManager()
        self.startup_manager = StartupManager(APP_NAME)
        self.tray_manager = TrayManager(self)

        self.root = None
        self.reminder_counter = 0
        self.countdown_labels = {}
        self.type_labels = {}
        self.current_page = None
        self.settings_dropdown = None

        self.init_ui()
        self.load_reminders()
        self.start_tray()
        self.update_countdowns()

    def init_ui(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title(APP_NAME)
        self.root.geometry("620x680")
        self.root.minsize(620, 600)

        try:
            if os.path.exists(ICON_PATH):
                self.root.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"设置窗口图标失败: {e}")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # ========== 主框架 ==========
        main_frame = ctk.CTkFrame(self.root, fg_color=COLOR_BG, corner_radius=0)
        main_frame.pack(fill="both", expand=True)

        # ========== 菜单栏 ==========
        self.create_menu_bar(main_frame)

        # ========== 内容区(动态切换页面) ==========
        self.content_frame = ctk.CTkFrame(main_frame, fg_color=COLOR_BG)
        self.content_frame.pack(fill="both", expand=True)

        # 默认显示主页面
        self.show_page("home")

    def create_menu_bar(self, parent):
        """创建顶部菜单栏"""
        menu_bar = ctk.CTkFrame(parent, fg_color=COLOR_CARD, height=44, corner_radius=0)
        menu_bar.pack(fill="x")
        menu_bar.pack_propagate(False)

        # 底部边框线
        border = ctk.CTkFrame(menu_bar, fg_color=COLOR_CARD_BORDER, height=1)
        border.pack(side="bottom", fill="x")

        # 主页面按钮
        self.home_btn = ctk.CTkButton(
            menu_bar, text="主页面",
            command=lambda: self.show_page("home"),
            fg_color="transparent",
            text_color=COLOR_TEXT_PRIMARY,
            hover_color="#E5E7EB",
            width=90, height=30,
            font=F(13, "bold"),
            corner_radius=0
        )
        self.home_btn.pack(side="left", padx=(10, 0), pady=7)

        # 设置按钮(带下拉箭头)
        self.settings_btn = ctk.CTkButton(
            menu_bar, text="设置  ▾",
            command=self.toggle_settings_menu,
            fg_color="transparent",
            text_color=COLOR_TEXT_PRIMARY,
            hover_color="#E5E7EB",
            width=90, height=30,
            font=F(13),
            corner_radius=0
        )
        self.settings_btn.pack(side="left", padx=0, pady=7)

    def toggle_settings_menu(self):
        """切换设置下拉菜单"""
        if self.settings_dropdown and self.settings_dropdown.winfo_exists():
            self.close_settings_menu()
            return

        # 计算按钮位置
        x = self.settings_btn.winfo_rootx()
        y = self.settings_btn.winfo_rooty() + self.settings_btn.winfo_height()

        # 创建下拉菜单窗口
        self.settings_dropdown = ctk.CTkToplevel(self.root)
        self.settings_dropdown.title("")
        self.settings_dropdown.geometry(f"160x100+{x}+{y}")
        self.settings_dropdown.overrideredirect(True)  # 无标题栏
        self.settings_dropdown.attributes("-topmost", True)
        self.settings_dropdown.configure(fg_color=COLOR_CARD)
        self.settings_dropdown.resizable(False, False)

        # 边框
        border_frame = ctk.CTkFrame(self.settings_dropdown, fg_color=COLOR_CARD, border_width=1, border_color=COLOR_CARD_BORDER, corner_radius=6)
        border_frame.pack(fill="both", expand=True)

        # 设置子菜单项
        item1 = ctk.CTkButton(
            border_frame, text="设置",
            command=lambda: [self.show_page("settings"), self.close_settings_menu()],
            fg_color="transparent",
            text_color=COLOR_TEXT_PRIMARY,
            hover_color="#E5E7EB",
            anchor="w",
            width=160, height=40,
            font=F(13),
            corner_radius=0
        )
        item1.pack(fill="x", padx=0, pady=(4, 0))

        item2 = ctk.CTkButton(
            border_frame, text="关于",
            command=lambda: [self.show_page("about"), self.close_settings_menu()],
            fg_color="transparent",
            text_color=COLOR_TEXT_PRIMARY,
            hover_color="#E5E7EB",
            anchor="w",
            width=160, height=40,
            font=F(13),
            corner_radius=0
        )
        item2.pack(fill="x", padx=0, pady=(0, 4))

        # 使用全局点击检测关闭下拉(延迟 150ms 避免打开菜单的点击被误判)
        self.root.after(150, self._bind_dropdown_outside_click)

    def _bind_dropdown_outside_click(self):
        """绑定全局点击事件以关闭下拉菜单"""
        if not self.settings_dropdown or not self.settings_dropdown.winfo_exists():
            return
        self.root.bind_all("<Button-1>", self._on_global_click, add="+")

    def _on_global_click(self, event):
        """全局点击事件处理"""
        if not self.settings_dropdown or not self.settings_dropdown.winfo_exists():
            return

        # 获取点击坐标
        try:
            x = event.x_root
            y = event.y_root
        except:
            return

        # 获取下拉菜单区域
        dd_x = self.settings_dropdown.winfo_rootx()
        dd_y = self.settings_dropdown.winfo_rooty()
        dd_w = self.settings_dropdown.winfo_width()
        dd_h = self.settings_dropdown.winfo_height()

        # 获取设置按钮区域
        btn_x = self.settings_btn.winfo_rootx()
        btn_y = self.settings_btn.winfo_rooty()
        btn_w = self.settings_btn.winfo_width()
        btn_h = self.settings_btn.winfo_height()

        # 如果点击在下拉菜单内或设置按钮上,不关闭
        if (dd_x <= x <= dd_x + dd_w and dd_y <= y <= dd_y + dd_h):
            return
        if (btn_x <= x <= btn_x + btn_w and btn_y <= y <= btn_y + btn_h):
            return

        # 点击外部,关闭下拉
        self.close_settings_menu()

    def close_settings_menu(self):
        """关闭设置下拉菜单"""
        try:
            self.root.unbind_all("<Button-1>")
        except:
            pass
        if self.settings_dropdown and self.settings_dropdown.winfo_exists():
            self.settings_dropdown.destroy()
        self.settings_dropdown = None

    def show_page(self, page_name):
        """切换页面"""
        # 清除当前页面
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # 清理可能已不存在的 widget 引用
        self.countdown_labels.clear()
        self.type_labels.clear()

        self.current_page = page_name

        if page_name == "home":
            self.build_home_page(self.content_frame)
            # 重新加载提醒卡片
            for r in self.data_manager.reminders:
                self.add_reminder_card(r)
            self.update_counter()
        elif page_name == "settings":
            self.build_settings_page(self.content_frame)
        elif page_name == "about":
            self.build_about_page(self.content_frame)

        # 更新菜单按钮高亮
        self._update_menu_highlight()

    def _update_menu_highlight(self):
        """更新菜单按钮高亮状态"""
        if self.current_page == "home":
            self.home_btn.configure(text_color=COLOR_TYPE_SCHEDULED, font=F(13, "bold"))
        else:
            self.home_btn.configure(text_color=COLOR_TEXT_PRIMARY, font=F(13, "bold"))

        if self.current_page in ("settings", "about"):
            self.settings_btn.configure(text_color=COLOR_TYPE_SCHEDULED, font=F(13, "bold"))
        else:
            self.settings_btn.configure(text_color=COLOR_TEXT_PRIMARY, font=F(13))

    def build_home_page(self, parent):
        """构建主页面(原主页内容)"""
        # ========== 顶部标题栏 ==========
        header_frame = ctk.CTkFrame(parent, fg_color=COLOR_BG, height=90)
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)

        left_header = ctk.CTkFrame(header_frame, fg_color=COLOR_BG)
        left_header.pack(side="left", padx=20, pady=15, anchor="w")

        # 应用图标(time.ico)
        try:
            if os.path.exists(ICON_PATH):
                app_img = Image.open(ICON_PATH)
                if app_img.mode != 'RGBA':
                    app_img = app_img.convert('RGBA')
                app_img = app_img.resize((56, 56), Image.Resampling.LANCZOS)
                app_ctk = CTkImage(light_image=app_img, dark_image=app_img, size=(56, 56))
                app_label = ctk.CTkLabel(left_header, image=app_ctk, text="")
                app_label.pack(side="left", padx=(0, 12))
        except Exception as e:
            print(f"加载应用图标失败: {e}")

        title_container = ctk.CTkFrame(left_header, fg_color=COLOR_BG)
        title_container.pack(side="left")

        title_row = ctk.CTkFrame(title_container, fg_color=COLOR_BG)
        title_row.pack(anchor="w")

        title_label = ctk.CTkLabel(
            title_row, text=APP_NAME,
            font=F(22, "bold"), text_color=COLOR_TEXT_PRIMARY
        )
        title_label.pack(side="left", padx=(0, 10))

        self.counter_label = ctk.CTkLabel(
            title_row, text="0/0 已启用",
            font=F(12), text_color=COLOR_TEXT_SECONDARY,
            fg_color="#E5E7EB", corner_radius=8, padx=10, pady=3
        )
        self.counter_label.pack(side="left")

        subtitle_label = ctk.CTkLabel(
            title_container,
            text="贴心提醒每一刻,助你养成好习惯",
            font=F(12), text_color=COLOR_TEXT_SECONDARY, anchor="w"
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

        # 新建按钮(实心蓝背景,白色文字)
        new_btn = ctk.CTkButton(
            header_frame, text="+ 新建提醒",
            command=self.show_new_reminder_dialog,
            width=120, height=38,
            font=F(14, "bold"),
            fg_color=COLOR_NEW_BG,
            text_color=COLOR_NEW_TEXT,
            hover_color=COLOR_NEW_HOVER,
            corner_radius=8
        )
        new_btn.pack(side="right", padx=20, pady=15)

        # ========== 提醒列表 ==========
        list_frame = ctk.CTkFrame(parent, fg_color=COLOR_BG)
        list_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self.scroll_frame = ctk.CTkScrollableFrame(
            list_frame, fg_color=COLOR_BG,
            scrollbar_button_color="#CBD5E1",
            scrollbar_button_hover_color=COLOR_TEXT_SECONDARY
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 8))

    def build_settings_page(self, parent):
        """构建设置页"""
        # 顶部标题
        header = ctk.CTkFrame(parent, fg_color=COLOR_BG, height=80)
        header.pack(fill="x", padx=20, pady=(15, 10))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="设置",
            font=F(24, "bold"), text_color=COLOR_TEXT_PRIMARY, anchor="w"
        ).pack(anchor="w", pady=(15, 0))

        # 设置项容器
        content = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=10,
                                border_width=1, border_color=COLOR_CARD_BORDER)
        content.pack(fill="x", padx=20, pady=10)

        # 开机自启项
        item = ctk.CTkFrame(content, fg_color=COLOR_CARD, height=70)
        item.pack(fill="x", padx=5, pady=5)
        item.pack_propagate(False)

        text_box = ctk.CTkFrame(item, fg_color=COLOR_CARD)
        text_box.pack(side="left", padx=15, pady=12)

        ctk.CTkLabel(text_box, text="开机自启",
                     font=F(15, "bold"), text_color=COLOR_TEXT_PRIMARY,
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(text_box, text="系统启动时自动运行",
                     font=F(12), text_color=COLOR_TEXT_SECONDARY,
                     anchor="w").pack(anchor="w")

        self.startup_var = ctk.BooleanVar(value=self.startup_manager.is_startup_enabled())
        startup_switch = ctk.CTkSwitch(
            item, text="", variable=self.startup_var,
            command=self.toggle_startup, width=50,
            progress_color=COLOR_TYPE_SCHEDULED,
            button_color="white", button_hover_color="#F3F4F6"
        )
        startup_switch.pack(side="right", padx=20, pady=15)

    def build_about_page(self, parent):
        """构建关于页"""
        # 顶部标题
        header = ctk.CTkFrame(parent, fg_color=COLOR_BG, height=80)
        header.pack(fill="x", padx=20, pady=(15, 10))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="关于",
            font=F(24, "bold"), text_color=COLOR_TEXT_PRIMARY, anchor="w"
        ).pack(anchor="w", pady=(15, 0))

        # 关于卡片
        content = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=10,
                                border_width=1, border_color=COLOR_CARD_BORDER)
        content.pack(fill="x", padx=20, pady=10)

        # 应用图标 + 名称
        info_top = ctk.CTkFrame(content, fg_color=COLOR_CARD)
        info_top.pack(fill="x", padx=20, pady=(25, 10))

        try:
            if os.path.exists(ICON_PATH):
                about_img = Image.open(ICON_PATH)
                if about_img.mode != 'RGBA':
                    about_img = about_img.convert('RGBA')
                about_img = about_img.resize((64, 64), Image.Resampling.LANCZOS)
                about_ctk = CTkImage(light_image=about_img, dark_image=about_img, size=(64, 64))
                ctk.CTkLabel(info_top, image=about_ctk, text="").pack(side="left", padx=(0, 15))
        except:
            pass

        text_box = ctk.CTkFrame(info_top, fg_color=COLOR_CARD)
        text_box.pack(side="left", pady=5)

        ctk.CTkLabel(text_box, text=APP_NAME,
                     font=F(20, "bold"), text_color=COLOR_TEXT_PRIMARY,
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(text_box, text=f"版本 v{APP_VERSION}",
                     font=F(13), text_color=COLOR_TEXT_SECONDARY,
                     anchor="w").pack(anchor="w", pady=(4, 0))

        # 分隔线
        sep = ctk.CTkFrame(content, fg_color=COLOR_CARD_BORDER, height=1)
        sep.pack(fill="x", padx=20, pady=10)

        # 介绍
        intro = ctk.CTkFrame(content, fg_color=COLOR_CARD)
        intro.pack(fill="x", padx=20, pady=(5, 25))

        ctk.CTkLabel(intro, text="一个轻量级提醒工具,帮你",
                     font=F(13), text_color=COLOR_TEXT_SECONDARY,
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(intro, text="准时、准时、再准时。",
                     font=F(13), text_color=COLOR_TEXT_SECONDARY,
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(intro, text="定时提醒 · 倒计时 · 循环提醒",
                     font=F(13), text_color=COLOR_TEXT_PRIMARY,
                     anchor="w").pack(anchor="w", pady=(8, 0))

    def update_counter(self):
        total = len(self.data_manager.reminders)
        enabled = sum(1 for r in self.data_manager.reminders if r.enabled)
        self.counter_label.configure(text=f"{enabled}/{total} 已启用")

    def add_reminder_card(self, reminder):
        """提醒卡片 - 三列分组布局:
        左: 图标 + 类型
        中: 标题 + 内容 + 倒计时
        右: 开关 + 编辑 + 删除"""
        # 根据提醒类型选择背景色
        card_bg = COLOR_CARD_BG_MAP.get(reminder.type, COLOR_CARD)
        card = ctk.CTkFrame(
            self.scroll_frame, fg_color=card_bg,
            corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER,
            height=130
        )
        card.pack(fill="x", padx=0, pady=4)
        card.pack_propagate(False)
        card.reminder_id = reminder.id

        # 类型名称和颜色
        type_names = {
            "scheduled": "定时提醒",
            "countdown": "倒计时",
            "loop": "循环提醒"
        }
        type_colors = {
            "scheduled": COLOR_TYPE_SCHEDULED,
            "countdown": COLOR_TYPE_COUNTDOWN,
            "loop": COLOR_TYPE_LOOP
        }

        # ========== 左列: 图标 + 类型 (整体垂直居中) ==========
        col1 = ctk.CTkFrame(card, fg_color=card_bg, width=80)
        col1.pack(side="left", fill="y", padx=(14, 8), pady=12)
        col1.pack_propagate(False)

        center_frame = ctk.CTkFrame(col1, fg_color=card_bg)
        center_frame.pack(expand=True)

        icon_img = IconGenerator.create_icon(reminder.type, 64)
        if icon_img:
            icon_ctk = CTkImage(light_image=icon_img, dark_image=icon_img, size=(64, 64))
            icon_label = ctk.CTkLabel(center_frame, image=icon_ctk, text="")
            icon_label.pack(pady=(0, 6))

        type_label = ctk.CTkLabel(
            center_frame,
            text=type_names.get(reminder.type, "提醒"),
            font=F(11, "bold"),
            text_color=type_colors.get(reminder.type, COLOR_TEXT_SECONDARY),
            anchor="w"
        )
        type_label.pack()
        self.type_labels[reminder.id] = type_label

        # ========== 中列: 标题 + 内容 + 倒计时 ==========
        col2 = ctk.CTkFrame(card, fg_color=card_bg)
        col2.pack(side="left", fill="both", expand=True, padx=0, pady=12)

        title_text = reminder.title if len(reminder.title) <= 24 else reminder.title[:24] + "..."
        title_label = ctk.CTkLabel(
            col2, text=title_text,
            font=F(15, "bold"), text_color=COLOR_TEXT_PRIMARY, anchor="w"
        )
        title_label.pack(anchor="w", pady=(0, 6))

        content_text = reminder.content if reminder.content else "(无内容)"
        # 限制最多 2 行(wraplength=300、font 12下,中文每行约 18 字 × 2 行 ≈ 36 字)
        if len(content_text) > 36:
            content_text = content_text[:36] + "..."
        content_label = ctk.CTkLabel(
            col2,
            text=content_text,
            font=F(12), text_color=COLOR_TEXT_SECONDARY, anchor="w",
            justify="left", wraplength=300
        )
        content_label.pack(anchor="w", fill="x")

        badge_text = "已停用" if not reminder.enabled else f"剩余 {reminder.format_remaining_time()}"
        badge_fg = COLOR_BADGE_DISABLED_TEXT if not reminder.enabled else COLOR_BADGE_COUNTDOWN_TEXT

        status_badge = ctk.CTkLabel(
            col2, text=badge_text,
            font=F(11, "bold"),
            text_color=badge_fg,
            fg_color="transparent", anchor="w"
        )
        status_badge.pack(anchor="w", pady=(4, 0))
        self.countdown_labels[reminder.id] = status_badge

        # ========== 右列: 开关 + 编辑 + 删除 ==========
        col3 = ctk.CTkFrame(card, fg_color=card_bg, width=90)
        col3.pack(side="right", fill="y", padx=(8, 14), pady=12)
        col3.pack_propagate(False)

        switch_var = ctk.BooleanVar(value=reminder.enabled)
        switch = ctk.CTkSwitch(
            col3, text="", variable=switch_var,
            width=70, switch_width=70, switch_height=26,
            progress_color=COLOR_TYPE_SCHEDULED,
            fg_color="#94A3B8",
            button_color="white",
            button_hover_color="#F1F5F9",
            command=lambda: self.toggle_reminder(reminder.id, switch_var.get())
        )
        switch.pack(anchor="w", pady=(0, 8))

        edit_btn = ctk.CTkButton(
            col3, text="编辑",
            width=70, height=28,
            font=F(11),
            fg_color=COLOR_EDIT_BG,
            text_color=COLOR_EDIT_TEXT,
            hover_color=COLOR_EDIT_HOVER,
            corner_radius=5,
            command=lambda: self.edit_reminder(reminder.id)
        )
        edit_btn.pack(pady=(0, 4))

        delete_btn = ctk.CTkButton(
            col3, text="删除",
            width=70, height=28,
            font=F(11),
            fg_color=COLOR_DELETE_BG,
            text_color=COLOR_DELETE_TEXT,
            hover_color=COLOR_DELETE_HOVER,
            corner_radius=5,
            command=lambda: self.delete_reminder(reminder.id)
        )
        delete_btn.pack(pady=4)

    def create_time_selector(self, parent, hour=0, minute=0, second=0):
        """创建时间选择器(时:分:秒 三个下拉框)"""
        # 小时
        hour_values = [str(i).zfill(2) for i in range(0, 24)]
        hour_combo = ctk.CTkComboBox(parent, values=hour_values, width=70, height=32,
                                      font=F(14), justify="center", dropdown_font=F(13))
        hour_combo.set(str(hour).zfill(2))
        hour_combo.pack(side="left", padx=3)

        ctk.CTkLabel(parent, text=":", font=F(16, "bold"),
                     text_color=COLOR_TEXT_SECONDARY).pack(side="left", padx=2)

        # 分钟
        minute_values = [str(i).zfill(2) for i in range(0, 60)]
        minute_combo = ctk.CTkComboBox(parent, values=minute_values, width=70, height=32,
                                        font=F(14), justify="center", dropdown_font=F(13))
        minute_combo.set(str(minute).zfill(2))
        minute_combo.pack(side="left", padx=3)

        ctk.CTkLabel(parent, text=":", font=F(16, "bold"),
                     text_color=COLOR_TEXT_SECONDARY).pack(side="left", padx=2)

        # 秒
        second_values = [str(i).zfill(2) for i in range(0, 60)]
        second_combo = ctk.CTkComboBox(parent, values=second_values, width=70, height=32,
                                        font=F(14), justify="center", dropdown_font=F(13))
        second_combo.set(str(second).zfill(2))
        second_combo.pack(side="left", padx=3)

        return hour_combo, minute_combo, second_combo

    def create_duration_input(self, parent, hour=0, minute=0, second=0, with_prefix=False):
        """创建时长输入(X 小时 X 分 X 秒)"""
        if with_prefix:
            prefix_label = ctk.CTkLabel(parent, text="每", font=F(14),
                                         text_color=COLOR_TEXT_PRIMARY)
            prefix_label.pack(side="left", padx=(0, 5))

        # 小时
        hour_entry = ctk.CTkEntry(parent, width=60, height=32, justify="center", font=F(14))
        hour_entry.pack(side="left", padx=3)
        hour_entry.insert(0, str(hour))

        hour_label = ctk.CTkLabel(parent, text="小时", font=F(12),
                                   text_color=COLOR_TEXT_SECONDARY)
        hour_label.pack(side="left", padx=(0, 8))

        # 分钟
        minute_entry = ctk.CTkEntry(parent, width=60, height=32, justify="center", font=F(14))
        minute_entry.pack(side="left", padx=3)
        minute_entry.insert(0, str(minute))

        minute_label = ctk.CTkLabel(parent, text="分", font=F(12),
                                     text_color=COLOR_TEXT_SECONDARY)
        minute_label.pack(side="left", padx=(0, 8))

        # 秒
        second_entry = ctk.CTkEntry(parent, width=60, height=32, justify="center", font=F(14))
        second_entry.pack(side="left", padx=3)
        second_entry.insert(0, str(second))

        second_label = ctk.CTkLabel(parent, text="秒", font=F(12),
                                     text_color=COLOR_TEXT_SECONDARY)
        second_label.pack(side="left", padx=(0, 5))

        return hour_entry, minute_entry, second_entry

    def show_new_reminder_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("新建提醒")
        dialog.geometry("420x520")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(fg_color=COLOR_BG)

        # 标题
        ctk.CTkLabel(dialog, text="新建提醒",
                     font=F(18, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(pady=(20, 15))

        # 类型选择
        ctk.CTkLabel(dialog, text="提醒类型", font=F(12, "bold"),
                     text_color=COLOR_TEXT_PRIMARY, anchor="w").pack(padx=30, pady=(5, 6), anchor="w")

        type_var = ctk.StringVar(value="scheduled")
        type_frame = ctk.CTkFrame(dialog, fg_color=COLOR_BG)
        type_frame.pack(padx=30, pady=3, anchor="w")

        ctk.CTkRadioButton(type_frame, text="定时提醒", variable=type_var, value="scheduled",
                           font=F(12), text_color=COLOR_TEXT_PRIMARY,
                           command=lambda: self.update_time_input(dialog, type_var.get(), time_frame)).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(type_frame, text="倒计时", variable=type_var, value="countdown",
                           font=F(12), text_color=COLOR_TEXT_PRIMARY,
                           command=lambda: self.update_time_input(dialog, type_var.get(), time_frame)).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(type_frame, text="循环", variable=type_var, value="loop",
                           font=F(12), text_color=COLOR_TEXT_PRIMARY,
                           command=lambda: self.update_time_input(dialog, type_var.get(), time_frame)).pack(side="left")

        # 时间设置区域(动态更新)
        time_label = ctk.CTkLabel(dialog, text="提醒时刻(时:分:秒)", font=F(12, "bold"),
                     text_color=COLOR_TEXT_PRIMARY, anchor="w")
        time_label.pack(padx=30, pady=(12, 6), anchor="w")

        time_frame = ctk.CTkFrame(dialog, fg_color=COLOR_BG)
        time_frame.pack(padx=30, pady=3, anchor="w", fill="x")
        # 初始创建定时提醒的时间选择器
        hour_combo, minute_combo, second_combo = self.create_time_selector(time_frame)

        # 保存引用以便在类型切换时更新
        dialog.time_inputs = (hour_combo, minute_combo, second_combo)
        dialog.time_frame = time_frame
        dialog.time_label = time_label

        # 标题
        ctk.CTkLabel(dialog, text="通知标题", font=F(12, "bold"),
                     text_color=COLOR_TEXT_PRIMARY, anchor="w").pack(padx=30, pady=(12, 6), anchor="w")

        title_entry = ctk.CTkEntry(dialog, placeholder_text="例如:喝水提醒", width=360, height=36,
                                    font=F(13))
        title_entry.pack(padx=30, pady=3, anchor="w")
        # 新建提醒默认标题
        title_entry.insert(0, "久坐提醒")

        # 内容
        ctk.CTkLabel(dialog, text="提醒内容", font=F(12, "bold"),
                     text_color=COLOR_TEXT_PRIMARY, anchor="w").pack(padx=30, pady=(10, 6), anchor="w")

        content_text = ctk.CTkTextbox(dialog, height=80, width=360, font=F(12))
        content_text.pack(padx=30, pady=3, anchor="w")
        # 新建提醒默认内容
        content_text.insert("1.0", "起身活动，放松眼睛，避免久坐。")

        # 按钮
        btn_frame = ctk.CTkFrame(dialog, fg_color=COLOR_BG)
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="取消", command=dialog.destroy, width=100, height=38,
                      font=F(13), fg_color="#E5E7EB", text_color=COLOR_TEXT_PRIMARY,
                      hover_color="#D1D5DB").pack(side="left", padx=6)

        def save_reminder():
            try:
                reminder_type = type_var.get()

                # 从 dialog.time_inputs 获取当前的时间输入控件
                hour_widget, minute_widget, second_widget = dialog.time_inputs

                if reminder_type == "scheduled":
                    hour = int(hour_widget.get())
                    minute = int(minute_widget.get())
                    second = int(second_widget.get())
                else:
                    hour = int(hour_widget.get()) if hour_widget.get() else 0
                    minute = int(minute_widget.get()) if minute_widget.get() else 0
                    second = int(second_widget.get()) if second_widget.get() else 0

                title = title_entry.get().strip()
                content = content_text.get("1.0", "end-1c").strip()

                if not title:
                    print("请输入通知标题")
                    return

                self.reminder_counter += 1
                reminder = Reminder(self.reminder_counter, reminder_type,
                                    hour, minute, second, title, content)
                self.data_manager.add_reminder(reminder)
                self.add_reminder_card(reminder)
                reminder.start(self.on_reminder_trigger)
                self.update_counter()
                dialog.destroy()
            except Exception as e:
                print(f"保存失败: {e}")

        ctk.CTkButton(btn_frame, text="保存", command=save_reminder, width=100, height=38,
                      font=F(13, "bold"), fg_color=COLOR_TYPE_SCHEDULED,
                      text_color="white", hover_color="#2563EB").pack(side="left", padx=6)

    def update_time_input(self, dialog, reminder_type, time_frame):
        """根据提醒类型更新时间输入控件"""
        # 销毁旧的时间输入控件
        for widget in time_frame.winfo_children():
            widget.destroy()

        # 更新标签
        if reminder_type == "scheduled":
            dialog.time_label.configure(text="提醒时刻(时:分:秒)")
            hour_combo, minute_combo, second_combo = self.create_time_selector(time_frame)
            dialog.time_inputs = (hour_combo, minute_combo, second_combo)
        elif reminder_type == "countdown":
            dialog.time_label.configure(text="倒计时时长(时:分:秒)")
            hour_entry, minute_entry, second_entry = self.create_duration_input(time_frame)
            dialog.time_inputs = (hour_entry, minute_entry, second_entry)
        elif reminder_type == "loop":
            dialog.time_label.configure(text="循环间隔(时:分:秒)")
            hour_entry, minute_entry, second_entry = self.create_duration_input(time_frame, with_prefix=True)
            dialog.time_inputs = (hour_entry, minute_entry, second_entry)

    def edit_reminder(self, reminder_id):
        reminder_to_edit = None
        for r in self.data_manager.reminders:
            if r.id == reminder_id:
                reminder_to_edit = r
                break
        if not reminder_to_edit:
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("编辑提醒")
        dialog.geometry("420x520")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(fg_color=COLOR_BG)

        ctk.CTkLabel(dialog, text="编辑提醒", font=F(18, "bold"),
                     text_color=COLOR_TEXT_PRIMARY).pack(pady=(20, 15))

        ctk.CTkLabel(dialog, text="提醒类型", font=F(12, "bold"),
                     text_color=COLOR_TEXT_PRIMARY, anchor="w").pack(padx=30, pady=(5, 6), anchor="w")

        type_var = ctk.StringVar(value=reminder_to_edit.type)
        type_frame = ctk.CTkFrame(dialog, fg_color=COLOR_BG)
        type_frame.pack(padx=30, pady=3, anchor="w")

        ctk.CTkRadioButton(type_frame, text="定时提醒", variable=type_var, value="scheduled",
                           font=F(12), text_color=COLOR_TEXT_PRIMARY,
                           command=lambda: self.update_time_input(dialog, type_var.get(), time_frame)).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(type_frame, text="倒计时", variable=type_var, value="countdown",
                           font=F(12), text_color=COLOR_TEXT_PRIMARY,
                           command=lambda: self.update_time_input(dialog, type_var.get(), time_frame)).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(type_frame, text="循环", variable=type_var, value="loop",
                           font=F(12), text_color=COLOR_TEXT_PRIMARY,
                           command=lambda: self.update_time_input(dialog, type_var.get(), time_frame)).pack(side="left")

        # 时间设置区域(动态更新)
        time_label = ctk.CTkLabel(dialog, text="", font=F(12, "bold"),
                     text_color=COLOR_TEXT_PRIMARY, anchor="w")
        time_label.pack(padx=30, pady=(12, 6), anchor="w")

        time_frame = ctk.CTkFrame(dialog, fg_color=COLOR_BG)
        time_frame.pack(padx=30, pady=3, anchor="w", fill="x")

        # 根据当前提醒类型创建对应的时间输入控件
        if reminder_to_edit.type == "scheduled":
            time_label.configure(text="提醒时刻(时:分:秒)")
            hour_combo, minute_combo, second_combo = self.create_time_selector(
                time_frame, reminder_to_edit.hour, reminder_to_edit.minute, reminder_to_edit.second)
            dialog.time_inputs = (hour_combo, minute_combo, second_combo)
        elif reminder_to_edit.type == "countdown":
            time_label.configure(text="倒计时时长(时:分:秒)")
            hour_entry, minute_entry, second_entry = self.create_duration_input(
                time_frame, reminder_to_edit.hour, reminder_to_edit.minute, reminder_to_edit.second)
            dialog.time_inputs = (hour_entry, minute_entry, second_entry)
        elif reminder_to_edit.type == "loop":
            time_label.configure(text="循环间隔(时:分:秒)")
            hour_entry, minute_entry, second_entry = self.create_duration_input(
                time_frame, reminder_to_edit.hour, reminder_to_edit.minute, reminder_to_edit.second, with_prefix=True)
            dialog.time_inputs = (hour_entry, minute_entry, second_entry)

        dialog.time_frame = time_frame
        dialog.time_label = time_label

        ctk.CTkLabel(dialog, text="通知标题", font=F(12, "bold"),
                     text_color=COLOR_TEXT_PRIMARY, anchor="w").pack(padx=30, pady=(12, 6), anchor="w")

        title_entry = ctk.CTkEntry(dialog, width=360, height=36, font=F(13))
        title_entry.pack(padx=30, pady=3, anchor="w")
        title_entry.insert(0, reminder_to_edit.title)

        ctk.CTkLabel(dialog, text="提醒内容", font=F(12, "bold"),
                     text_color=COLOR_TEXT_PRIMARY, anchor="w").pack(padx=30, pady=(10, 6), anchor="w")

        content_text = ctk.CTkTextbox(dialog, height=80, width=360, font=F(12))
        content_text.pack(padx=30, pady=3, anchor="w")
        content_text.insert("1.0", reminder_to_edit.content)

        btn_frame = ctk.CTkFrame(dialog, fg_color=COLOR_BG)
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="取消", command=dialog.destroy, width=100, height=38,
                      font=F(13), fg_color="#E5E7EB", text_color=COLOR_TEXT_PRIMARY,
                      hover_color="#D1D5DB").pack(side="left", padx=6)

        def update_reminder():
            try:
                reminder_to_edit.stop()
                reminder_to_edit.type = type_var.get()

                # 从 dialog.time_inputs 获取当前的时间输入控件
                hour_widget, minute_widget, second_widget = dialog.time_inputs

                if reminder_to_edit.type == "scheduled":
                    reminder_to_edit.hour = int(hour_widget.get())
                    reminder_to_edit.minute = int(minute_widget.get())
                    reminder_to_edit.second = int(second_widget.get())
                else:
                    reminder_to_edit.hour = int(hour_widget.get()) if hour_widget.get() else 0
                    reminder_to_edit.minute = int(minute_widget.get()) if minute_widget.get() else 0
                    reminder_to_edit.second = int(second_widget.get()) if second_widget.get() else 0

                reminder_to_edit.title = title_entry.get().strip()
                reminder_to_edit.content = content_text.get("1.0", "end-1c").strip()

                if not reminder_to_edit.title:
                    print("请输入通知标题")
                    return

                reminder_to_edit.calculate_next_trigger()
                if reminder_to_edit.enabled:
                    reminder_to_edit.start(self.on_reminder_trigger)

                self.data_manager.update_reminder(reminder_to_edit)
                self.refresh_list()
                dialog.destroy()
            except Exception as e:
                print(f"更新失败: {e}")

        ctk.CTkButton(btn_frame, text="保存", command=update_reminder, width=100, height=38,
                      font=F(13, "bold"), fg_color=COLOR_TYPE_SCHEDULED,
                      text_color="white", hover_color="#2563EB").pack(side="left", padx=6)

    def delete_reminder(self, reminder_id):
        for r in self.data_manager.reminders:
            if r.id == reminder_id:
                r.stop()
                break

        if reminder_id in self.countdown_labels:
            del self.countdown_labels[reminder_id]
        if reminder_id in self.type_labels:
            del self.type_labels[reminder_id]

        self.data_manager.remove_reminder(reminder_id)
        self.refresh_list()
        self.update_counter()

    def toggle_reminder(self, reminder_id, enabled):
        for r in self.data_manager.reminders:
            if r.id == reminder_id:
                r.enabled = enabled
                if enabled:
                    r.calculate_next_trigger()
                    r.start(self.on_reminder_trigger)
                else:
                    r.stop()
                self.data_manager.update_reminder(r)
                if reminder_id in self.countdown_labels:
                    label = self.countdown_labels[reminder_id]
                    if enabled:
                        label.configure(text=f"剩余 {r.format_remaining_time()}",
                                         fg_color=COLOR_BADGE_COUNTDOWN_BG,
                                         text_color=COLOR_BADGE_COUNTDOWN_TEXT)
                    else:
                        label.configure(text="已停用",
                                         fg_color=COLOR_BADGE_DISABLED_BG,
                                         text_color=COLOR_BADGE_DISABLED_TEXT)
                self.update_counter()
                break

    def refresh_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.countdown_labels.clear()
        self.type_labels.clear()
        for r in self.data_manager.reminders:
            self.add_reminder_card(r)

    def load_reminders(self):
        """启动所有提醒的计时器(卡片由 show_page 创建)"""
        if self.data_manager.reminders:
            self.reminder_counter = max(r.id for r in self.data_manager.reminders)
        for r in self.data_manager.reminders:
            if r.enabled:
                r.start(self.on_reminder_trigger)
        self.update_counter()

    def update_countdowns(self):
        """每秒实时更新所有倒计时"""
        try:
            for r in self.data_manager.reminders:
                if r.id in self.countdown_labels and r.enabled:
                    self.countdown_labels[r.id].configure(text=f"剩余 {r.format_remaining_time()}")
        except:
            pass
        if self.root:
            self.root.after(1000, self.update_countdowns)

    def on_reminder_trigger(self, reminder):
        """触发Windows原生通知(无弹窗)"""
        self.notification_manager.send_notification(reminder.title, reminder.content)

    def toggle_startup(self):
        if self.startup_var.get():
            self.startup_manager.enable_startup()
        else:
            self.startup_manager.disable_startup()

    def start_tray(self):
        threading.Thread(target=self.tray_manager.run, daemon=True).start()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def on_closing(self):
        self.root.withdraw()

    def quit_app(self):
        for r in self.data_manager.reminders:
            r.stop()
        self.data_manager.save()
        if self.tray_manager.icon:
            self.tray_manager.icon.stop()
        self.root.quit()
        sys.exit(0)

    def run(self):
        self.root.mainloop()

def ensure_single_instance():
    """单实例检测:若已有一个实例在运行,激活其窗口并退出当前实例。
    使用 Windows 命名互斥体(ctypes 标准库,无额外依赖)。
    """
    mutex_name = "Global\\TimeClock_SingleInstance_v1"
    kernel32 = ctypes.windll.kernel32
    ERROR_ALREADY_EXISTS = 183
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        # 已有实例在运行,尝试激活其窗口(标题为 APP_NAME)
        try:
            user32 = ctypes.windll.user32
            SW_RESTORE = 9
            hwnd = user32.FindWindowW(None, APP_NAME)
            if hwnd:
                # 无论窗口是开着/最小化/托盘隐藏(withdraw),都先恢复显示再置前
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        sys.exit(0)
    return mutex

if __name__ == "__main__":
    _SINGLE_INSTANCE_MUTEX = ensure_single_instance()
    TimeClockApp().run()
