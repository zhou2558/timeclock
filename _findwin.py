import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

titles = []

def enum_cb(hwnd, lparam):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        titles.append((hwnd, buf.value))
    return True

user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

print("=== 包含'提醒'或'Time'的窗口 ===")
for hwnd, t in titles:
    if "提醒" in t or "Time" in t or "助手" in t:
        print(f"HWND={hwnd} TITLE={t!r}")

print("=== FindWindowW(None, '提醒助手') ===")
hwnd = user32.FindWindowW(None, "提醒助手")
print("HWND =", hwnd, "(0 表示没找到)")

print("=== 用 c_void_p 作为 restype 再试 ===")
user32.FindWindowW.restype = ctypes.c_void_p
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
hwnd2 = user32.FindWindowW(None, "提醒助手")
print("HWND(void_p) =", hwnd2)
