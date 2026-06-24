import re
with open('in89_dump.html', 'r', encoding='utf-8') as f:
    html = f.read()
# 找 theater_api input
for m in re.finditer(r'<input[^>]*name="theater_api"[^>]*>', html):
    print('theater_api:', m.group(0))
for m in re.finditer(r'<input[^>]*name="theater_id"[^>]*>', html):
    print('theater_id:', m.group(0))
for m in re.finditer(r'<input[^>]*name="is_connect"[^>]*>', html):
    print('is_connect:', m.group(0))