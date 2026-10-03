import re

# 读取 README.md
with open("README.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 提取所有标题（## 到 ######，跳过一级标题 #，因为一级标题通常只出现一次）
headings = []
for line in lines:
    match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
    if match:
        level = len(match.group(1))
        title = match.group(2).strip()
        # 去掉标题里可能存在的 Markdown 格式符号
        title = re.sub(r"[*_`\[\]]", "", title)
        headings.append((level, title))

# 如果没有任何标题，直接退出
if not headings:
    print("没有找到任何标题，请检查 README.md 的格式。")
    exit()

# 确定最小标题层级，作为侧边栏的“根”
min_level = min(h[0] for h in headings)

# 生成锚点：Docsify 的规则是转小写、去标点、空格转 -
def make_anchor(title):
    anchor = title.lower()
    # 去掉常见标点（中英文）
    anchor = re.sub(r"[，。！？、；：""''（）《》【】\.,!\?;:\(\)\[\]{}<>\"'`~@#$%^&*+=|\\/]", "", anchor)
    # 空格转 -
    anchor = anchor.replace(" ", "-")
    return anchor

# 生成 _sidebar.md
output = []
for level, title in headings:
    # 跳过和最小层级相同的第一个标题（通常是文档标题，不适合放在侧边栏）
    # 如果你希望它出现，把下面这行注释掉
    if level == min_level and title == headings[0][1]:
        continue
    indent = "  " * (level - min_level - 1)
    anchor = make_anchor(title)
    output.append(f"{indent}* [{title}](README.md#{anchor})")

with open("_sidebar.md", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print(f"已生成 _sidebar.md，共 {len(output)} 个条目。")