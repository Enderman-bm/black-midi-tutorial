# -*- coding: utf-8 -*-
"""
docx -> Markdown 转换助手（供维护组使用，需安装 Pandoc）

用法:
    python docx2md.py 稿件.docx [-o 输出.md]

做三件事:
1. 调用 Pandoc 转换 docx（gfm 输出，表格兼容 docsify）；
2. 提取文档内嵌图片，按 docs/media 现有编号顺延命名（如 image131.png）复制入库，
   并把图片引用改写为 ![描述](media/imageN.png)；
3. 把 Word 高亮 ==…== 转换为仓库统一写法 <span class="mark">…</span>。

转换完成后：合并进 docs/ 对应章节，并运行
    python fix_toc_and_spacing.py --apply
做格式收尾。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(ROOT, "docs", "media")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def next_image_number():
    """扫描 docs/media 现有编号，返回下一个可用编号"""
    mx = 0
    for f in os.listdir(MEDIA_DIR):
        m = re.match(r"image(\d+)\.png$", f)
        if m:
            mx = max(mx, int(m.group(1)))
    return mx + 1


def convert(docx_path, out_path):
    if shutil.which("pandoc") is None:
        sys.exit("未找到 Pandoc。请先安装：winget install --id JohnMacFarlane.Pandoc（或见 https://pandoc.org/installing.html）")

    tmp = tempfile.mkdtemp(prefix="docx2md-")
    tmp_md = os.path.join(tmp, "out.md")
    tmp_media = os.path.join(tmp, "media")

    print("调用 Pandoc 转换...")
    subprocess.run(
        [
            "pandoc", docx_path,
            "-f", "docx", "-t", "gfm", "--wrap=none",
            f"--extract-media={tmp_media}",
            "-o", tmp_md,
        ],
        check=True,
    )
    text = open(tmp_md, encoding="utf-8").read()

    # ---------- 图片：入库 + 改写引用 ----------
    num = next_image_number()
    mapping = {}
    copied = []

    def map_image(src):
        nonlocal num
        if src in mapping:
            return mapping[src]
        real = src if os.path.isabs(src) else os.path.join(tmp, src.replace("/", os.sep))
        if not os.path.isfile(real):
            print(f"  !! 找不到提取的图片: {src}")
            mapping[src] = src
            return src
        name = f"image{num}.png"
        shutil.copyfile(real, os.path.join(MEDIA_DIR, name))
        mapping[src] = f"media/{name}"
        copied.append(name)
        num += 1
        return mapping[src]

    def figure_repl(m):
        block = m.group(0)
        img = re.search(r"<img[^>]*>", block)
        if not img:
            return block
        tag = img.group(0)
        src = re.search(r'src="([^"]+)"', tag).group(1)
        alt_m = re.search(r'alt="([^"]*)"', tag)
        alt = alt_m.group(1) if alt_m else ""
        return f"![{alt}]({map_image(src)})"

    def img_repl(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag).group(1)
        alt_m = re.search(r'alt="([^"]*)"', tag)
        alt = alt_m.group(1) if alt_m else ""
        return f"![{alt}]({map_image(src)})"

    text = re.sub(r"<figure>.*?</figure>", figure_repl, text, flags=re.S)
    text = re.sub(r"<img[^>]+>", img_repl, text)

    def md_img_repl(m):
        alt, src = m.group(1), m.group(2)
        if src.startswith(("http://", "https://", "media/", "data:")):
            return m.group(0)
        return f"![{alt}]({map_image(src)})"

    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", md_img_repl, text)

    # ---------- 高亮 ==…== -> span（跳过代码围栏与行内代码） ----------
    out_lines = []
    in_fence = False
    fence = ""
    n_mark = 0
    for ln in text.split("\n"):
        mf = re.match(r"^\s*(```+|~~~+)", ln)
        if mf:
            marker = mf.group(1)[0]
            if not in_fence:
                in_fence, fence = True, marker
            elif marker == fence:
                in_fence = False
            out_lines.append(ln)
            continue
        if not in_fence:
            parts = ln.split("`")
            for i in range(0, len(parts), 2):
                n_mark += len(re.findall(r"==([^=\n]+)==", parts[i]))
                parts[i] = re.sub(
                    r"==([^=\n]+)==",
                    lambda m: f'<span class="mark">{m.group(1)}</span>',
                    parts[i],
                )
            ln = "`".join(parts)
        out_lines.append(ln)
    text = "\n".join(out_lines)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

    print("完成。")
    print(f"  图片入库: {len(copied)} 张" + (f"（{', '.join(copied)}）" if copied else ""))
    print(f"  高亮转换: {n_mark} 处")
    print(f"  输出文件: {out_path}")
    print()
    print("下一步：合并进 docs/ 对应章节，然后运行：")
    print("  python fix_toc_and_spacing.py --apply")
    print("  python fix_toc_and_spacing.py")
    print("提示：转换/合并前请先 git pull；一次只处理一份投稿并及时推送，避免编号与他人分配冲突。")


def main():
    ap = argparse.ArgumentParser(description="docx 转 Markdown（含图片入库与引用改写）")
    ap.add_argument("docx", help="待转换的 .docx 文件")
    ap.add_argument("-o", "--output", help="输出的 .md 路径（默认为输入文件同目录同名）")
    args = ap.parse_args()

    if not os.path.isfile(args.docx):
        sys.exit(f"文件不存在: {args.docx}")
    out = args.output or os.path.splitext(args.docx)[0] + ".md"
    convert(args.docx, out)


if __name__ == "__main__":
    main()
