"""把 ../gubacoffee 的 Django 網站輸出成靜態檔到 docs/，給 GitHub Pages 用。

用法：
    .venv/bin/python build.py              # 原始碼預設在 ../gubacoffee
    .venv/bin/python build.py /path/to/src # 指定原始碼位置

原 repo 不需要做任何修改。
"""
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1] if len(sys.argv) > 1 else HERE.parent / "gubacoffee").resolve()
OUT = HERE / "docs"

LANG = "zh-hant"
# 要輸出的頁面：Django URL 路徑片段 -> 輸出資料夾（"" 代表語言首頁）
PAGES = ["", "about", "products", "rental", "ourfactory", "courses"]

# 寫入 CNAME；不綁網域就設成 None（改用 https://derick0823.github.io/gubacoffee-site/）
DOMAIN = "gu8coffee.com"

# 沒被任何頁面引用、又超過這個大小的 asset 不複製（避免 repo 塞滿原始大圖）
SKIP_UNREFERENCED_OVER = 5 * 1024 * 1024


def setup_django():
    if not (SRC / "manage.py").exists():
        sys.exit(f"找不到 Django 專案：{SRC}")
    sys.path.insert(0, str(SRC))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gubacoffee.settings")
    import django

    django.setup()
    from django.conf import settings

    settings.ALLOWED_HOSTS = ["*"]
    return settings


def rewrite(html: str, depth: int) -> str:
    """把站內絕對路徑改成相對路徑，讓網站在子路徑（username.github.io/repo/）和自訂網域都能用。"""
    prefix = "../" * depth or "./"

    # 拿掉語言切換表單（POST 表單在靜態網站無法運作；目前也只有中文）
    html = re.sub(r'<form name="set_language".*?</form>', "", html, flags=re.S)

    # /assets//xxx -> /assets/xxx
    html = html.replace("/assets//", "/assets/")

    # 頁面連結：/zh-hant/about -> ../about/（加結尾斜線，免得多一次轉址）
    def page_link(m):
        slug = m.group(2)
        target = f"{LANG}/{slug}/" if slug else f"{LANG}/"
        return f"{m.group(1)}{prefix}{target}"

    html = re.sub(rf'(["\'])/{LANG}/([\w-]*)(?=["\'#?])', page_link, html)

    # 靜態資源：/assets/... -> ../../assets/...
    html = re.sub(r'(["\'(])/assets/', rf"\1{prefix}assets/", html)
    return html


def build_pages(settings):
    from django.test import Client

    client = Client()
    referenced = set()
    for slug in PAGES:
        url = f"/{LANG}/{slug}"
        resp = client.get(url)
        if resp.status_code != 200:
            sys.exit(f"{url} 回傳 {resp.status_code}")
        html = resp.content.decode("utf-8")
        referenced.update(re.findall(r"/assets/+([^\"')\s?#]+)", html))

        rel = Path(LANG) / slug if slug else Path(LANG)
        depth = len(rel.parts)
        dest = OUT / rel / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rewrite(html, depth), encoding="utf-8")
        print(f"  {url:<22} -> {dest.relative_to(HERE)}")
    return referenced


def copy_assets(settings, referenced):
    from urllib.parse import unquote

    referenced = {unquote(p) for p in referenced}
    src = Path(settings.STATIC_DIR)
    dst = OUT / "assets"
    skipped = []
    for f in src.rglob("*"):
        if not f.is_file() or f.name == ".DS_Store":
            continue
        rel = f.relative_to(src).as_posix()
        if f.stat().st_size > SKIP_UNREFERENCED_OVER and rel not in referenced:
            skipped.append((rel, f.stat().st_size))
            continue
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
    for rel, size in skipped:
        print(f"  略過未引用大檔：{rel} ({size / 1024 / 1024:.1f} MB)")


def write_extras():
    (OUT / "index.html").write_text(
        f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<title>古8咖啡</title>
<meta http-equiv="refresh" content="0; url={LANG}/">
<link rel="canonical" href="{LANG}/">
</head><body><a href="{LANG}/">古8咖啡</a></body></html>
""",
        encoding="utf-8",
    )
    # 讓 GitHub Pages 不經過 Jekyll，直接發佈原檔
    (OUT / ".nojekyll").write_text("")
    if DOMAIN:
        (OUT / "CNAME").write_text(DOMAIN + "\n")


def main():
    print(f"原始碼：{SRC}")
    settings = setup_django()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    print("輸出頁面：")
    referenced = build_pages(settings)
    print("複製 assets：")
    copy_assets(settings, referenced)
    write_extras()
    print(f"完成 -> {OUT}")


if __name__ == "__main__":
    main()
