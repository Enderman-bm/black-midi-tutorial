# -*- coding: utf-8 -*-
"""
修复侧边栏锚点 + 正文格式规范化（本地与 GitHub Actions 共用）

用法:
    python fix_toc_and_spacing.py          # 仅检查，输出将修复的问题
    python fix_toc_and_spacing.py --apply  # 实际写入

做的事:
1. 按 docsify@4 真实 slugify 规则重算 docs/*.md 全部标题锚点
   （小写A-Z -> 去HTML标签 -> 去特定标点[保留全角标点] -> 空白转- ->
    合并- -> 数字开头加_ -> 同页重名 -1/-2）
2. 修正 docs/SUMMARY.md 与 docs/_sidebar.md 的锚点（保留显示文本与缩进）
3. 规范化 docs/*.md 标题前空行: ## 前空5行, ### 前空3行
   （公式块/代码块内部不处理）
4. 规范化其他格式: pandoc 遗留公式写法、图片引用路径、裸链接（加尖括号）、文件末尾换行
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs")
APPLY = "--apply" in sys.argv

# ---------------------------------------------------------------- slugify
RE_PUNCT = re.compile("[\u2000-\u206F\u2E00-\u2E7F\\\\'!\"#$%&()*+,./:;<=>?@\\[\\]^`{|}~]")


def docsify_slug(text):
    """docsify@4 (4.13.x) slugify 的精确复刻"""
    # marked 内联解析: 反斜杠转义的 ASCII 标点 -> 字面量
    s = re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])", r"\1", text)
    s = s.strip()
    s = re.sub(r"[A-Z]+", lambda m: m.group(0).lower(), s)
    s = re.sub(r"<[^>]+>", "", s)
    s = RE_PUNCT.sub("", s)
    s = re.sub(r"\s", "-", s)
    s = re.sub(r"-+", "-", s)
    s = re.sub(r"^(\d)", r"_\1", s)
    return s


def extract_headings(lines):
    """提取 h1-h3 标题原文（跳过 ``` / ~~~ 代码围栏内部）"""
    pat = re.compile(r"^(#{1,3}) (.+?)\s*$")
    out = []
    in_fence = False
    fence = ""
    for ln in lines:
        mf = re.match(r"^\s*(```+|~~~+)", ln)
        if mf:
            marker = mf.group(1)[0]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence = False
            continue
        if in_fence:
            continue
        m = pat.match(ln)
        if m:
            out.append((len(m.group(1)), m.group(2)))
    return out


def split_keep_eol(content):
    """返回 (lines, eol)，保留原始换行风格"""
    if "\r\n" in content:
        return content.split("\r\n"), "\r\n"
    return content.split("\n"), "\n"


# ---------------------------------------------------------------- 侧边栏修复
SIDEBAR_RE = re.compile(r"^(\s*)\* \[(.+?)\]\(([^)#]+)(?:#(.*))?\)\s*$")


def fix_sidebar(text):
    lines, eol = split_keep_eol(text)
    # 逐行解析，记录 (行号, 匹配)
    parsed = []
    for i, ln in enumerate(lines):
        m = SIDEBAR_RE.match(ln)
        parsed.append((i, m))

    # 按文件分组（保持出现顺序）
    groups = []
    for i, m in parsed:
        if not m:
            continue
        fname = m.group(3)
        if not groups or groups[-1][0] != fname:
            groups.append((fname, []))
        groups[-1][1].append((i, m))

    fixed = []
    problems = []
    new_line_at = {}  # 行号 -> 新行文本
    for fname, items in groups:
        path = os.path.join(DOCS, fname)
        if not os.path.isfile(path):
            problems.append(f"文件不存在: {fname}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            fcontent = f.read()
        flines, _ = split_keep_eol(fcontent)
        heads = extract_headings(flines)
        if len(heads) != len(items):
            problems.append(
                f"{fname}: 侧边栏条目 {len(items)} 个, 文档标题 {len(heads)} 个, 无法按顺序对齐"
            )
            continue
        cache = {}
        for (li, m), (lv, htext) in zip(items, heads):
            indent, disp = m.group(1), m.group(2)
            old_anchor = m.group(4)
            base = docsify_slug(htext)
            n = cache.get(base, -1)
            cache[base] = n + 1
            exp_anchor = base if n < 0 else f"{base}-{n + 1}"
            if old_anchor is None:
                # 原条目本来就没有锚点（如一级标题直链文件），保持风格
                new_line_at[li] = f"{indent}* [{disp}]({m.group(3)})"
                continue
            if old_anchor != exp_anchor:
                fixed.append((fname, disp, old_anchor, exp_anchor))
            new_line_at[li] = f"{indent}* [{disp}]({fname}#{exp_anchor})"

    if not new_line_at and not problems:
        return None, [], []

    out_lines = [new_line_at.get(i, ln) for i, ln in enumerate(lines)]
    return eol.join(out_lines), fixed, problems


# ---------------------------------------------------------------- 空行规范化
def fix_spacing(content):
    lines, eol = split_keep_eol(content)
    out = []
    in_fence = False
    fence = ""
    changed = 0
    for ln in lines:
        mf = re.match(r"^\s*(```+|~~~+)", ln)
        if mf:
            marker = mf.group(1)[0]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence = False
            out.append(ln)
            continue
        if not in_fence:
            desired = None
            if re.match(r"^## ", ln):
                desired = 5
            elif re.match(r"^### ", ln):
                desired = 3
            if desired is not None:
                old_n = 0
                while out and out[-1] == "" and old_n < 50:
                    out.pop()
                    old_n += 1
                if old_n != desired:
                    changed += 1
                out.extend([""] * desired)
        out.append(ln)
    return eol.join(out), changed


# ---------------------------------------------------------------- 内容格式规范化
# 裸链接中不应出现的字符（全角标点 / 中日韩文字），出现即说明链接吞掉了后续文字
URL_STOP = set("），。；：？！、》《「」『』“”‘’（）【】…")
BARE_URL_RE = re.compile(r"(?<!\]\()(?<![<`A-Za-z0-9_])(https?://\S+)")


def _wrap_bare_url(m):
    """裸链接后若紧跟中文或全角标点（会被渲染吞入链接），自动用尖括号截断"""
    url = m.group(1)
    cut = len(url)
    for idx, ch in enumerate(url):
        if ch in URL_STOP or "\u4e00" <= ch <= "\u9fff":
            cut = idx
            break
    if cut == len(url):
        return m.group(0)
    return "<" + url[:cut] + ">" + url[cut:]


def fix_content(content):
    """规范化公式写法、图片引用路径与文件末尾换行"""
    eol = "\r\n" if "\r\n" in content else "\n"
    norm = content.replace("\r\n", "\n") if eol == "\r\n" else content
    changes = []

    # 1) pandoc 遗留行内公式 $`...`$ -> $...$
    norm, n = re.subn(r"\$`([^`\n]+)`\$", r"$\1$", norm)
    if n:
        changes.append(f"行内公式写法 {n} 处")

    # 2) ```math 代码块 -> $$...$$
    norm, n = re.subn(
        r"```\s*math\s*\n(.*?)\n```",
        lambda m: "$$\n" + m.group(1) + "\n$$",
        norm,
        flags=re.DOTALL,
    )
    if n:
        changes.append(f"math 代码块 {n} 处")

    # 3) 图片引用路径 ./media/、../media/ -> media/
    norm, n = re.subn(r"\]\((?:\.{1,2}/)+media/", "](media/", norm)
    if n:
        changes.append(f"图片路径 {n} 处")

    # 4) 裸链接修复（跳过代码围栏）
    out_lines = []
    in_fence = False
    fence = ""
    n_url = 0
    for ln_ in norm.split("\n"):
        mf = re.match(r"^\s*(```+|~~~+)", ln_)
        if mf:
            marker = mf.group(1)[0]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence = False
            out_lines.append(ln_)
            continue
        if not in_fence:
            new_ln = BARE_URL_RE.sub(_wrap_bare_url, ln_)
            if new_ln != ln_:
                n_url += 1
                ln_ = new_ln
        out_lines.append(ln_)
    if n_url:
        changes.append(f"裸链接加尖括号 {n_url} 处")
        norm = "\n".join(out_lines)

    # 5) 文件末尾确保换行
    if norm and not norm.endswith("\n"):
        norm += "\n"
        changes.append("补文件末尾换行")

    result = norm.replace("\n", "\r\n") if eol == "\r\n" else norm
    return result, changes


def main():
    # 1. 侧边栏
    for name in ("SUMMARY.md", "_sidebar.md"):
        path = os.path.join(DOCS, name)
        if not os.path.isfile(path):
            print(f"[跳过] {name} 不存在")
            continue
        with open(path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        fixed_doc, fixed, problems = fix_sidebar(content)
        print(f"=== {name} ===")
        print(f"需修正锚点: {len(fixed)} 条")
        for fn, disp, old, new in fixed:
            print(f"  [{fn}] {disp}")
            print(f"      {old}  ->  {new}")
        for p in problems:
            print(f"  !! {p}")
        if APPLY and fixed_doc is not None:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(fixed_doc)
            print(f"  已写入 {name}")
        print()

    # 2. 正文格式规范化（标题空行 + 公式/图片路径/末尾换行）
    docs_files = sorted(
        f for f in os.listdir(DOCS)
        if f.endswith(".md") and f not in ("SUMMARY.md", "_sidebar.md")
    )
    print("=== 正文格式规范化（标题空行: ## 前5行 / ### 前3行；公式、图片路径等） ===")
    for fn in docs_files:
        path = os.path.join(DOCS, fn)
        with open(path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        new_content, changed = fix_spacing(content)
        new_content, changes = fix_content(new_content)
        if changed or changes:
            desc = []
            if changed:
                desc.append(f"标题间距 {changed} 处")
            desc.extend(changes)
            print(f"  {fn}: " + "，".join(desc))
            if APPLY:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(new_content)
    print("完成。" + ("" if APPLY else " (未写入, 加 --apply 生效)"))


if __name__ == "__main__":
    main()
