import re

with open("README.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

def shift_number(match):
    hashes = match.group(1)
    number_str = match.group(2)
    title = match.group(3)
    parts = number_str.rstrip('.').split('.')
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return match.group(0)
    # 第一级加 1，子级不变
    parts[0] = parts[0] + 1
    new_number = '.'.join(str(p) for p in parts)
    return f"{hashes} {new_number} {title}"

pattern = re.compile(r"^(#{1,6})\s+(\d+(?:\.\d+)*)\s+(.+)$")

new_lines = []
for line in lines:
    m = pattern.match(line.strip())
    if m:
        new_lines.append(shift_number(m) + "\n")
    else:
        new_lines.append(line)

with open("README.md", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("已把所有标题的第一级编号加 1。")