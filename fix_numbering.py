import re

# 读取 README.md
with open("README.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 第一步：删除 "# 1 关于本文档Markdown使用说明" 这一节
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if re.match(r"^#\s+1\s+关于本文档Markdown使用说明", line.strip()):
        start_idx = i
    elif start_idx is not None and re.match(r"^#\s+2\s+", line.strip()):
        end_idx = i
        break

if start_idx is not None and end_idx is not None:
    del lines[start_idx:end_idx]
    print(f"已删除 '# 1 关于本文档Markdown使用说明'（第 {start_idx+1} 到 {end_idx} 行）")
elif start_idx is not None:
    del lines[start_idx:]
    print(f"已删除 '# 1 关于本文档Markdown使用说明'（从第 {start_idx+1} 行到末尾）")
else:
    print("未找到 '# 1 关于本文档Markdown使用说明'，跳过删除步骤。")

# 第二步：把所有标题的【第一级】编号减 1，子级保持不变
def shift_number(match):
    hashes = match.group(1)
    number_str = match.group(2)
    title = match.group(3)

    parts = number_str.rstrip('.').split('.')
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return match.group(0)

    # 只减第一级
    parts[0] = parts[0] - 1
    # 如果第一级变成 0，说明这个标题本来就不该有编号，跳过
    if parts[0] <= 0:
        return None

    new_number = '.'.join(str(p) for p in parts)
    return f"{hashes} {new_number} {title}"

pattern = re.compile(r"^(#{1,6})\s+(\d+(?:\.\d+)*)\s+(.+)$")

new_lines = []
for line in lines:
    stripped = line.strip()
    m = pattern.match(stripped)
    if m:
        result = shift_number(m)
        if result is None:
            # 第一级减完是 0，说明是目录那一节或无效标题，直接跳过
            continue
        new_lines.append(result + "\n")
    else:
        new_lines.append(line)

with open("README.md", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("已将所有标题的第一级编号减 1，子级保持不变。")

# 第三步：重新生成 _sidebar.md
headings = []
for line in new_lines:
    m = re.match(r"^(#{1,6})\s+(\d+(?:\.\d+)*)\s+(.+)$", line.strip())
    if m:
        level = len(m.group(1))
        number = m.group(2)
        title = m.group(3).strip()
        headings.append((level, number, title))

if not headings:
    print("没有找到任何带编号的标题，_sidebar.md 未生成。")
    exit()

min_level = min(h[0] for h in headings)

def make_anchor(number, title):
    text = f"{number} {title}".lower()
    text = re.sub(r"[，。！？、；：""''（）《》【】\.,!\?;:\(\)\[\]{}<>\"'`~@#$%^&*+=|\\/]", "", text)
    text = text.replace(" ", "-")
    return text

output = []
for level, number, title in headings:
    indent = "  " * (level - min_level - 1)
    display = f"{number} {title}"
    anchor = make_anchor(number, title)
    output.append(f"{indent}* [{display}](README.md#{anchor})")

with open("_sidebar.md", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print(f"已重新生成 _sidebar.md，共 {len(output)} 个条目。")