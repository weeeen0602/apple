import re
with open('in89_dump.html', 'r', encoding='utf-8') as f:
    html = f.read()
# 找所有 script src
for m in re.finditer(r'<script[^>]*src=["\']([^"\']+)["\']', html):
    print(m.group(1))
print('---')
# 找 inline script 區塊
for m in re.finditer(r'<script(?![^>]*src=)[^>]*>(.*?)</script>', html, re.DOTALL):
    body = m.group(1)
    if 'api' in body or 'axios' in body or 'fetch' in body:
        print('INLINE SCRIPT with api/fetch:')
        print(body[:500])
        print('---')