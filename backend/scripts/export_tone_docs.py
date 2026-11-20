"""把 T-One 平台上的「帮助文档」导出成 Markdown，作为检索语料。

T-One 前端（tone-front）里帮助文档的接口是：
    GET /api/sys/help_doc/?doc_type=help_doc&page_size=1000   → 文档列表（id、title …）
    GET /api/sys/help_doc/?id=14                              → data[0].content 是 HTML 正文
公网的 https://tone.openanolis.cn 不登录也能访问帮助文档；自己部署的 T-One 可能要带 Cookie。

用法：
    python scripts/export_tone_docs.py --base-url https://tone.openanolis.cn --out data/tone_docs
"""
import argparse
import json
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


class HTMLToMarkdown(HTMLParser):
    """够用的 HTML → Markdown：保留标题层级、列表、代码块，丢掉图片和样式。"""

    BLOCK = {"p", "div", "br", "tr", "table", "blockquote", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.in_pre = False
        self.skip = 0  # <script>/<style> 里的内容不要

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif re.fullmatch(r"h[1-6]", tag):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag == "pre":
            self.in_pre = True
            self.out.append("\n\n```\n")
        elif tag == "code" and not self.in_pre:
            self.out.append("`")
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
        elif re.fullmatch(r"h[1-6]", tag) or tag in ("p", "div", "table"):
            self.out.append("\n\n")
        elif tag == "pre":
            self.in_pre = False
            self.out.append("\n```\n\n")
        elif tag == "code" and not self.in_pre:
            self.out.append("`")
        elif tag in ("td", "th"):
            self.out.append(" | ")

    def handle_data(self, data):
        if self.skip:
            return
        self.out.append(data if self.in_pre else re.sub(r"\s+", " ", data))

    def markdown(self) -> str:
        text = "".join(self.out)
        text = re.sub(r"[ \t]+\n", "\n", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()


def html_to_markdown(html: str) -> str:
    parser = HTMLToMarkdown()
    parser.feed(html or "")
    return parser.markdown()


def get_json(url: str, cookie: str = "") -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "tone-assistant-rag", "Cookie": cookie})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="https://tone.openanolis.cn")
    p.add_argument("--out", default="data/tone_docs")
    p.add_argument("--doc-type", default="help_doc", help="help_doc（帮助文档）或 notice（公告）")
    p.add_argument("--cookie", default="", help="私有部署需要登录时，从浏览器复制 Cookie")
    args = p.parse_args()

    base = args.base_url.rstrip("/")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    listing = get_json(f"{base}/api/sys/help_doc/?doc_type={args.doc_type}&page_size=1000", args.cookie)
    docs = listing.get("data") or []
    print(f"共 {len(docs)} 篇 {args.doc_type}")
    for item in docs:
        detail = get_json(f"{base}/api/sys/help_doc/?id={item['id']}", args.cookie)
        doc = (detail.get("data") or [{}])[0]
        title = (doc.get("title") or item.get("title") or f"doc-{item['id']}").strip()
        body = html_to_markdown(doc.get("content", ""))
        front = f"---\ntitle: {title}\nurl: {base}/{args.doc_type}/{item['id']}\n---\n\n"
        (out / f"{item['id']}.md").write_text(front + f"# {title}\n\n{body}\n", encoding="utf-8")
        print(f"  ✓ {item['id']:>4}  {title}  ({len(body)} 字)")
        time.sleep(0.3)  # 别把人家服务器打爆
    print(f"已保存到 {out.resolve()}")


if __name__ == "__main__":
    main()
