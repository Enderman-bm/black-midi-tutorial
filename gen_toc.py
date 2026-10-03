import re

# 读取 README.md
with open("README.md", "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")

# 第一步：扫描所有标题，确定层级结构
headings = []
for i, line in enumerate(lines):
    match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
    if match:
        level = len(match.group(1))
        title = match.group(2).strip()
        # 去掉标题里已有的编号（如果有）
        title = re.sub(r"^[\d\.]+\s+", "", title)
        headings.append({"line_index": i, "level": level, "title": title})

if not headings:
    print("没有找到任何标题。")
    exit()

# 确定最小标题层级
min_level = min(h["level"] for h in headings)

# 第二步：给标题编号
counters = [0] * 7  # 支持最多 6 级标题

for h in headings:
    level = h["level"]
    # 计算相对层级（0-based）
    rel = level - min_level

    # 只处理到 min_level + 3 的层级（可调整）
    if rel > 3:
        h["number"] = ""
        continue

    counters[rel] += 1
    # 重置更深层级的计数器
    for j in range(rel + 1, 7):
        counters[j] = 0

    # 生成编号，如 1.2.3
    number = ".".join(str(counters[k]) for k in range(rel + 1))
    h["number"] = number

# 第三步：把编号写回正文标题
for h in headings:
    if not h["number"]:
        continue
    old_line = lines[h["line_index"]]
    prefix = "#" * h["level"]
    lines[h["line_index"]] = f"{prefix} {h['number']} {h['title']}"

with open("README.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

# 第四步：生成带编号的 _sidebar.md
def make_anchor(title):
    anchor = title.lower()
    anchor = re.sub(r"[，。！？、；：""''（）《》【】\.,!\?;:\(\)\[\]{}<>\"'`~@#$%^&*+=|\\/]", "", anchor)
    anchor = anchor.replace(" ", "-")
    return anchor

output = []
for h in headings:
    if not h["number"]:
        continue
    indent = "  " * (h["level"] - min_level - 1)
    title_with_number = f"{h['number']} {h['title']}"
    anchor = make_anchor(title_with_number)
    output.append(f"{indent}* [{title_with_number}](README.md#{anchor})")

with open("_sidebar.md", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print(f"完成：{len([h for h in headings if h['number']])} 个标题已编号，_sidebar.md 已生成。")