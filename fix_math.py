import re, os

DOCS_DIR = "docs"

for fname in os.listdir(DOCS_DIR):
    if not fname.endswith(".md"):
        continue
    path = os.path.join(DOCS_DIR, fname)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 1. 行内公式：$`...`$ → $...$
    content = re.sub(r"\$`([^`]+)`\$", r"$\1$", content)

    # 2. 块级公式：``` math ... ``` → $$...$$
    content = re.sub(r"```\s*math\s*\n(.*?)\n```", r"$$\n\1\n$$", content, flags=re.DOTALL)

    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"已修复 {fname}")

print("完成。")
