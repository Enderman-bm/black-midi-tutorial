# -*- coding: utf-8 -*-
"""
版本号自动更新（供 GitHub Actions 在合并/推送时调用）

规则:
- 版本号格式：年-月-日-当日序号，如 26-10-04-01（序号两位，同日递增，跨日重置）
- 同时更新 docs/00-前言.md 的「版本号」行与 README.md 的「当前版本 **…**」
- 时区按北京时间（Asia/Shanghai）

用法:
    python bump_version.py
"""
import os
import re
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
FOREWORD = os.path.join(ROOT, "docs", "00-前言.md")
README = os.path.join(ROOT, "README.md")

VERSION_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})(?:-(\d{1,3}))?(?:-REL)?$")
FOREWORD_RE = re.compile(r"^(版本号)([0-9\-REL]+)\s*$", re.M)
README_RE = re.compile(r"(当前版本 \*\*)([0-9\-REL]+)(\*\*)")

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Asia/Shanghai")
except Exception:
    TZ = timezone(timedelta(hours=8))


def next_version(current, today):
    """current: 当前版本字符串；today: datetime.date；返回新版本字符串"""
    m = VERSION_RE.match(current)
    if not m:
        raise ValueError(f"无法解析当前版本号: {current!r}")
    date_part = f"{today:%y-%m-%d}"
    if f"{m.group(1)}-{m.group(2)}-{m.group(3)}" == date_part:
        nn = int(m.group(4) or 0) + 1
    else:
        nn = 1
    return f"{date_part}-{nn:02d}"


def main():
    with open(FOREWORD, "r", encoding="utf-8", newline="") as f:
        fw = f.read()
    m = FOREWORD_RE.search(fw)
    if not m:
        sys.exit("未能在 docs/00-前言.md 找到「版本号……」行")
    current = m.group(2)
    new = next_version(current, datetime.now(TZ).date())

    fw_new = FOREWORD_RE.sub(lambda mm: f"{mm.group(1)}{new}", fw, count=1)
    with open(FOREWORD, "w", encoding="utf-8", newline="") as f:
        f.write(fw_new)

    with open(README, "r", encoding="utf-8", newline="") as f:
        rd = f.read()
    if not README_RE.search(rd):
        sys.exit("未能在 README.md 找到「当前版本 **……**」")
    rd_new = README_RE.sub(lambda mm: f"{mm.group(1)}{new}{mm.group(3)}", rd, count=1)
    with open(README, "w", encoding="utf-8", newline="") as f:
        f.write(rd_new)

    print(f"版本号已更新: {current} -> {new}")


if __name__ == "__main__":
    main()
