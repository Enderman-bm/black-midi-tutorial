# -*- coding: utf-8 -*-
"""
版本号自动更新（供 GitHub Actions 在合并/推送时调用）

规则:
- 普通版本：年-月-日-当日序号，如 26-10-04-01（序号两位，同日递增，跨日重置）
- Release 版本：在版本号后加 -REL，如 26-10-04-01-REL，表示可对外分发的正式版本
- 同时更新 docs/00-前言.md 的「版本号」行与 README.md 的「当前版本 **…**」
- 时区按北京时间（Asia/Shanghai）

用法:
    python bump_version.py            # 递增版本号（合并/推送时自动调用）
    python bump_version.py --release  # 将当前版本标记为 Release（追加 -REL 后缀）
"""
import os
import re
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
FOREWORD = os.path.join(ROOT, "docs", "00-前言.md")
README = os.path.join(ROOT, "README.md")

VERSION_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})(?:-(\d{1,3}))?(?:-REL)?$")
# 注意：结束位置必须精确停在版本号本身，不能带 \s*$（会吞掉行尾与空行）
FOREWORD_RE = re.compile(r"^(版本号)(\d{2}-\d{2}-\d{2}(?:-\d{1,3})?(?:-REL)?)", re.M)
README_RE = re.compile(r"(当前版本 \*\*)(\d{2}-\d{2}-\d{2}(?:-\d{1,3})?(?:-REL)?)(\*\*)")

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Asia/Shanghai")
except Exception:
    TZ = timezone(timedelta(hours=8))


def next_version(current, today):
    """current: 当前版本字符串；today: datetime.date；返回递增后的新版本字符串"""
    m = VERSION_RE.match(current)
    if not m:
        raise ValueError(f"无法解析当前版本号: {current!r}")
    date_part = f"{today:%y-%m-%d}"
    if f"{m.group(1)}-{m.group(2)}-{m.group(3)}" == date_part:
        nn = int(m.group(4) or 0) + 1
    else:
        nn = 1
    return f"{date_part}-{nn:02d}"


def _read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def get_current():
    """读取前言中的当前版本号"""
    fw = _read(FOREWORD)
    m = FOREWORD_RE.search(fw)
    if not m:
        sys.exit("未能在 docs/00-前言.md 找到「版本号……」行")
    return m.group(2)


def apply_version(current, new):
    """把两个文件中的版本号从 current 替换为 new"""
    fw = _read(FOREWORD)
    m = FOREWORD_RE.search(fw)
    if not m:
        sys.exit("未能在 docs/00-前言.md 找到「版本号……」行")
    if m.group(2) != current:
        sys.exit(f"前言中的版本号({m.group(2)})与预期({current})不一致")
    fw_new = FOREWORD_RE.sub(lambda mm: f"{mm.group(1)}{new}", fw, count=1)
    _write(FOREWORD, fw_new)

    rd = _read(README)
    if not README_RE.search(rd):
        sys.exit("未能在 README.md 找到「当前版本 **……**」")
    rd_new = README_RE.sub(lambda mm: f"{mm.group(1)}{new}{mm.group(3)}", rd, count=1)
    _write(README, rd_new)


def main():
    current = get_current()
    new = next_version(current, datetime.now(TZ).date())
    apply_version(current, new)
    print(f"版本号已更新: {current} -> {new}")


def mark_release():
    current = get_current()
    if current.endswith("-REL"):
        sys.exit(f"当前版本已是 Release: {current}")
    new = current + "-REL"
    apply_version(current, new)
    print(f"已标记 Release: {current} -> {new}")


if __name__ == "__main__":
    if "--release" in sys.argv[1:]:
        mark_release()
    else:
        main()
