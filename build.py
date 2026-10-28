"""Build a self-contained public guide. No credentials or backend connection required."""

import html
import re
import shutil
from pathlib import Path

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

ROOT = Path(__file__).parent
BASE = 'https://dev.coders.kr/'
REPO = 'https://github.com/coders-kr/coders-core-v2-guide'
SECTIONS = ['integration', 'quickstart', 'github', 'app-versions', 'budget', 'permissions', 'backend', 'errors', 'support', 'checklist']


def build():
    markdown = MarkdownIt('commonmark', {'html': False}).enable('table')
    source = (ROOT / 'guide.md').read_text()
    tokens = markdown.parse(source)
    toc, anchors, seen = [], [], set()
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            title = tokens[i+1].content.replace('`', '')
            if token.tag == 'h1':
                identifier = 'guide-title'
            elif token.tag == 'h2':
                identifier = SECTIONS[len(toc)]
                toc.append((identifier, re.sub(r'^\d+\.\s*', '', title)))
            else:
                identifier = 'frontend' if title == '프론트 처리' else re.sub(r'[^\w-]', '-', title).strip('-')
            if identifier in seen:
                raise ValueError(f'Duplicate heading: {identifier}')
            seen.add(identifier)
            token.attrSet('id', identifier)
            if token.tag != 'h1':
                anchors.append(identifier)
        if token.type == 'inline':
            for child in token.children or []:
                if child.type == 'link_open':
                    href = child.attrGet('href') or ''
                    if href.startswith(BASE + '#'):
                        child.attrSet('href', href[len(BASE):])
                    elif href.startswith('https://'):
                        child.attrSet('target', '_blank')
                        child.attrSet('rel', 'noopener noreferrer')

    def code_block(items, idx, options, env):
        token = items[idx]
        language = token.info.strip().split()[0] if token.info.strip() else 'text'
        try:
            lexer = get_lexer_by_name(language)
        except ClassNotFound:
            lexer = TextLexer()
        code = highlight(token.content, lexer, HtmlFormatter(nowrap=True))
        label = {'bash':'Shell', 'json':'JSON', 'html':'HTML', 'python':'Python', 'text':'Text'}.get(language, language)
        return (
            '<figure class="code-block"><figcaption><span>' + html.escape(label) + '</span>'
            '<button class="copy-code" type="button" aria-label="코드 복사">복사</button></figcaption>'
            '<pre><code class="language-' + html.escape(language, quote=True) + '">' + code + '</code></pre></figure>\n'
        )

    markdown.renderer.rules['fence'] = code_block
    markdown.renderer.rules['table_open'] = lambda *args: '<div class="table-scroll" tabindex="0" aria-label="표"><table>\n'
    markdown.renderer.rules['table_close'] = lambda *args: '</table></div>\n'
    content = markdown.renderer.render(tokens, markdown.options, {})
    for identifier in anchors:
        # Insert a copyable native section link without changing the heading text.
        pattern = r'(<h[23] id="' + re.escape(identifier) + r'">)(.*?)(</h[23]>)'
        content = re.sub(pattern, lambda m: m[1] + m[2] + '<a class="heading-anchor" href="#' + identifier + '" aria-label="이 절 링크">#</a>' + m[3], content)
    links = ''.join(f'<a href="#{identifier}"><span>{i+1:02}</span>{html.escape(title)}</a>' for i,(identifier,title) in enumerate(toc))
    document = f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Coders Core v2 프로젝트 명세, GitHub 실행, ASGI·프론트 연동, 계좌·예산·권한과 재시도 규약을 안내합니다.">
<meta name="theme-color" content="#ffffff">
<meta property="og:type" content="website">
<meta property="og:title" content="Coders Core v2 호환 개발 가이드">
<meta property="og:description" content="코드와 프론트를 Coders에 연결하는 개발자 가이드. 로그인 없이 바로 읽어보세요.">
<meta property="og:url" content="{BASE}">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; base-uri 'self'; form-action 'none'">
<title>Coders Core v2 · 호환 개발 가이드</title>
<link rel="canonical" href="{BASE}">
<link rel="icon" href="./assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="./assets/style.css">
<script src="./assets/app.js" defer></script>
</head>
<body id="top">
<a class="skip-link" href="#content">본문으로 건너뛰기</a>
<header class="site-header"><div class="header-inner">
<a class="brand" href="#top" aria-label="Coders 개발자 문서 처음으로">/coders.kr<span>Core v2</span></a>
<nav class="header-links" aria-label="외부 링크">
<a class="api-link" href="https://core-v2.coders.kr/openapi.json" target="_blank" rel="noopener noreferrer">API 규격 ↗</a>
<a href="{REPO}" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
<button id="theme-toggle" type="button" aria-label="다크 모드로 전환">◐</button>
</nav></div></header>
<div class="page-layout">
<aside class="sidebar"><details class="toc" open><summary>이 문서의 내용</summary><div class="toc-content">
<p class="sidebar-label">DEVELOPER GUIDE</p><nav aria-label="문서 목차">{links}</nav>
<a class="download-link" href="./guide.md" download>Markdown 다운로드 ↓</a>
</div></details></aside>
<main id="content" class="prose"><div class="eyebrow">DEVELOPER GUIDE <span>공개 문서</span></div>
{content}
<footer class="article-footer"><span>/coders.kr · Core v2</span><a href="{REPO}/edit/main/guide.md" target="_blank" rel="noopener noreferrer">문서 수정 제안 ↗</a></footer>
</main></div>
<a class="back-top" href="#top" aria-label="문서 맨 위로" hidden>↑</a>
<div id="copy-status" class="sr-only" role="status" aria-live="polite"></div>
</body></html>'''
    output = ROOT / '_site'
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    shutil.copytree(ROOT / 'assets', output / 'assets')
    shutil.copy2(ROOT / 'guide.md', output / 'guide.md')
    (output / 'index.html').write_text(document)
    activity = markdown.render((ROOT / 'activity.md').read_text())
    (output / 'activity.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>워크스페이스 활동 · Coders</title><style>body{font:16px/1.8 system-ui;max-width:900px;margin:48px auto;padding:0 24px;color:#18191c}pre{overflow:auto;background:#f5f5f6;padding:20px;border-radius:10px}a{color:inherit}</style><a href="/">← 개발자 가이드</a><main>' + activity + '</main></html>')
    shutil.copy2(ROOT / 'activity.md', output / 'activity.md')
    shutil.copy2(ROOT / 'agent-connect.py', output / 'agent-connect.py')
    shutil.copy2(ROOT / 'activity-example.zip', output / 'activity-example.zip')

    (output / '.nojekyll').touch()
    (output / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n')
    (output / 'sitemap.xml').write_text(f'<?xml version="1.0" encoding="utf-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{BASE}</loc></url></urlset>')
    if len(toc) != len(SECTIONS):
        raise ValueError('Unexpected guide section count')
    print(f'Built {len(toc)} sections into {output}/index.html')


if __name__ == '__main__':
    build()
