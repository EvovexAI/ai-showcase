# -*- coding: utf-8 -*-
"""HTML → 可读 Markdown 转换器（提取正文，保留标题/段落/表格/代码块/列表）。
用法: python convert-html-to-md.py <input.html> <output.md>
"""
import sys, re
from html.parser import HTMLParser


class MDConverter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0
        self.in_pre = False
        self.pre_buf = []
        self.in_table = False
        self.table_rows = []
        self.row = []
        self.cell = []
        self.in_cell = False
        self.in_li = False
        self.li_started = False
        self.list_stack = []
        self.last_was_blank = True

    def emit(self, s):
        self.out.append(s)

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'svg', 'canvas', 'iframe', 'nav', 'header', 'footer'):
            self.skip += 1
            return
        if self.skip:
            return
        if tag == 'pre':
            self.in_pre = True
            self.pre_buf = []
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.emit('\n\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'p':
            self.emit('\n\n')
        elif tag == 'br':
            self.emit('\n')
        elif tag == 'hr':
            self.emit('\n\n---\n\n')
        elif tag == 'table':
            self.in_table = True
            self.table_rows = []
        elif tag == 'tr':
            self.row = []
        elif tag in ('td', 'th'):
            self.in_cell = True
            self.cell = []
        elif tag in ('ul', 'ol'):
            self.list_stack.append(tag)
        elif tag == 'li':
            self.emit('\n' + ('- ' if (not self.list_stack or self.list_stack[-1] == 'ul') else '1. '))
        elif tag == 'code' and not self.in_pre:
            self.emit('`')
        elif tag in ('strong', 'b'):
            self.emit('**')
        elif tag in ('em', 'i'):
            self.emit('*')
        elif tag in ('img',):
            self.emit('[图]')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg', 'canvas', 'iframe', 'nav', 'header', 'footer'):
            if self.skip:
                self.skip -= 1
            return
        if self.skip:
            return
        if tag == 'pre':
            self.in_pre = False
            code = ''.join(self.pre_buf)
            code = re.sub(r'\n{3,}', '\n\n', code).strip('\n')
            self.emit('\n\n```\n' + code + '\n```\n\n')
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.emit('\n')
        elif tag == 'p':
            self.emit('\n')
        elif tag == 'table':
            self.in_table = False
            self._flush_table()
        elif tag == 'tr':
            pass
        elif tag in ('td', 'th'):
            self.in_cell = False
            self.row.append(re.sub(r'\s+', ' ', ''.join(self.cell)).strip())
        elif tag in ('ul', 'ol'):
            if self.list_stack:
                self.list_stack.pop()
            self.emit('\n')
        elif tag == 'code' and not self.in_pre:
            self.emit('`')
        elif tag in ('strong', 'b'):
            self.emit('**')
        elif tag in ('em', 'i'):
            self.emit('*')

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_pre:
            self.pre_buf.append(data)
        elif self.in_cell:
            self.cell.append(data)
        else:
            self.emit(data)

    def _flush_table(self):
        if not self.table_rows or not self.table_rows[0]:
            return
        # 规范化列数
        ncol = max(len(r) for r in self.table_rows)
        rows = [r + [''] * (ncol - len(r)) for r in self.table_rows]
        self.emit('\n\n')
        self.emit('| ' + ' | '.join(rows[0]) + ' |\n')
        self.emit('|' + '---|' * ncol + '\n')
        for r in rows[1:]:
            self.emit('| ' + ' | '.join(r) + ' |\n')
        self.emit('\n')

    def close(self):
        super().close()
        if self.in_table and self.table_rows:
            self._flush_table()


def clean(text):
    # 合并过密的空行、去除行尾空格、把段落间多余空行压缩为最多两个
    text = text.replace('\xa0', ' ')
    lines = [l.rstrip() for l in text.split('\n')]
    out = []
    blank = 0
    for l in lines:
        if not l.strip():
            blank += 1
            if blank <= 1:
                out.append('')
        else:
            blank = 0
            out.append(l)
    return '\n'.join(out).strip() + '\n'


def main():
    if len(sys.argv) != 3:
        print('用法: python convert-html-to-md.py <input.html> <output.md>')
        sys.exit(1)
    with open(sys.argv[1], 'r', encoding='utf-8', errors='replace') as f:
        html = f.read()
    p = MDConverter()
    p.feed(html)
    p.close()
    md = clean(''.join(p.out))
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'OK: {sys.argv[2]} ({len(md)} chars)')


if __name__ == '__main__':
    main()
