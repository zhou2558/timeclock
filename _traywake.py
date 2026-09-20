import ctypes, time, subprocess, os
from ctypes import wintypes
user32 = ctypes.windll.user32
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
WM_CLOSE = 0x0010

def find_visible():
    res = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lp):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n > 0:
                buf = ctypes.create_unicode_buffer(n+1)
                user32.GetWindowTextW(hwnd, buf, n+1)
                if buf.value == "提醒助手":
                    res.append(hwnd)
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return res

exe = r"E:\工作资料\Qclaw\202607\20260706\TimeClock打包\dist\TimeClock\TimeClock.exe"
print("[1] 启动实例1 ...")
p1 = subprocess.Popen([exe])
time.sleep(6)
print("    实例1可见窗口:", [hex(h) for h in find_visible()])
hwnds = find_visible()
assert hwnds, "实例1窗口没起来!"
hwnd = hwnds[0]
print("[2] 发送 WM_CLOSE (触发退回托盘) ...")
user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
time.sleep(2)
print("    关窗后可见窗口:", find_visible(), "(应为空)")
print("[3] 启动实例2 (应被单实例拦截并唤醒实例1) ...")
p2 = subprocess.Popen([exe])
time.sleep(4)
print("    实例2 是否存活:", p2.poll() is None, "(应为 False=已退出)")
print("    唤醒后可见窗口:", [hex(h) for h in find_visible()], "(应非空=被拉回)")
print("[4] 系统 TimeClock 进程数:", len([1 for _ in __import__('os').popen('tasklist /fi \"IMAGENAME eq TimeClock.exe\"').read().splitlines() if 'TimeClock.exe' in _]))
# 清理
for p in (p1, p2):
    try: p.kill()
    except Exception: pass
