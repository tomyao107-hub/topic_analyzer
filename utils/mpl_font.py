"""
matplotlib 中文字体配置工具
在任何绘图前调用 setup_mpl_chinese() 即可解决中文方块问题
"""
import os
import sys
import matplotlib
# 必须在导入 pyplot 前设置后端
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from utils.logger import get_logger

logger = get_logger()

# Windows 常见中文字体候选列表（按优先级排序）
_FONT_CANDIDATES = [
    "Microsoft YaHei",   # 微软雅黑（Windows）
    "SimHei",            # 黑体（Windows）
    "SimSun",            # 宋体（Windows）
    "KaiTi",             # 楷体（Windows）
    "FangSong",          # 仿宋（Windows）
    "PingFang SC",       # 苹方（macOS）
    "Heiti SC",          # 黑体（macOS）
    "Noto Sans CJK SC",  # Linux
    "WenQuanYi Micro Hei",  # Linux
    "Source Han Sans SC",
    "Arial Unicode MS",
]

_configured = False


def _find_cjk_font() -> str:
    """扫描系统字体，返回第一个可用的中文字体名"""
    from matplotlib import font_manager as fm

    # 刷新字体缓存（首次运行）
    try:
        fm.fontManager.addfont  # 检查是否支持
    except AttributeError:
        pass

    available = {f.name for f in fm.fontManager.ttflist}

    for name in _FONT_CANDIDATES:
        if name in available:
            logger.info(f"[mpl_font] 找到中文字体：{name}")
            return name

    # 二次扫描：检查字体文件名（针对某些 Linux 环境）
    system_dirs = []
    if sys.platform == "win32":
        system_dirs = [
            r"C:\Windows\Fonts",
        ]
    elif sys.platform == "darwin":
        system_dirs = [
            "/Library/Fonts",
            "/System/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ]
    else:
        system_dirs = [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
        ]

    cjk_keywords = ["cjk", "chinese", "hans", "hant", "heiti", "simhei",
                     "simsun", "yahei", "wenquanyi", "pingfang", "noto"]
    for d in system_dirs:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for fname in files:
                if fname.lower().endswith((".ttf", ".otf")):
                    lower = fname.lower()
                    if any(kw in lower for kw in cjk_keywords):
                        fpath = os.path.join(root, fname)
                        try:
                            fm.fontManager.addfont(fpath)
                            prop = fm.FontProperties(fname=fpath)
                            font_name = prop.get_name()
                            logger.info(f"[mpl_font] 手动加载字体：{fpath} -> {font_name}")
                            return font_name
                        except Exception:
                            pass

    logger.warning("[mpl_font] 未找到中文字体，图表中文可能显示为方块")
    return ""


def setup_mpl_chinese():
    """
    配置 matplotlib 中文字体，应在第一次绘图前调用。
    幂等：多次调用不会重复配置。
    """
    global _configured
    if _configured:
        return

    font_name = _find_cjk_font()
    if font_name:
        plt.rcParams["font.family"] = "sans-serif"
        # 把找到的字体放在列表第一位
        existing = plt.rcParams.get("font.sans-serif", [])
        if isinstance(existing, str):
            existing = [existing]
        plt.rcParams["font.sans-serif"] = [font_name] + [
            f for f in existing if f != font_name
        ]

    # 修复负号显示为方块的问题
    plt.rcParams["axes.unicode_minus"] = False

    _configured = True
    logger.info(f"[mpl_font] matplotlib 中文字体配置完成：{font_name or '(未找到，使用默认)'}")
