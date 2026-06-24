from playwright.sync_api import sync_playwright
import time, json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://www.in89cinemax.com/film_list.aspx?TheaterId=2&type=Hot', timeout=60000, wait_until='domcontentloaded')
    time.sleep(5)
    movies = page.eval_on_selector_all('.movie_info', '''els => els.map(el => {
        const ps = el.querySelectorAll('p');
        return {
            cn_name: ps[0]?.textContent?.trim(),
            en_name: ps[1]?.textContent?.trim(),
            version: ps[2]?.textContent?.trim(),
            runtime: ps[3]?.textContent?.trim(),
            rating: ps[4]?.textContent?.trim(),
            release: ps[5]?.textContent?.trim(),
            img: el.querySelector('img')?.src,
            href: el.querySelector('a')?.href,
        };
    })''')
    print(f'共 {len(movies)} 部電影:')
    for i, m in enumerate(movies, 1):
        cn = m.get('cn_name', '')
        en = m.get('en_name', '')
        rel = m.get('release', '')
        print(f'{i}. {cn} ({en}) - {rel}')
    with open('in89_movies.json', 'w', encoding='utf-8') as f:
        json.dump(movies, f, ensure_ascii=False, indent=2)
    print('saved to in89_movies.json')
    browser.close()