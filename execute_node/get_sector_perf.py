import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json

async def extract_sector_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # True로 설정하면 브라우저 UI가 표시되지 않음
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        page = await context.new_page()
        await page.goto("https://finviz.com/groups.ashx?g=sector&v=140&o=name", wait_until="domcontentloaded", timeout=10000)
    
        # await page.goto("https://finviz.com/groups.ashx", wait_until="networkidle") # wait for all network requests to finish
        await page.wait_for_timeout(1000)  # 1초만 대기 (필요시 1500~2000ms로 조절)

        # 렌더링된 HTML 가져오기
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.groups_table")
    if not table:
        print("❌ 테이블을 찾지 못했습니다.")
        return

    headers = [th.get_text(strip=True) for th in table.select("thead th")]
    # print("✅ 추출된 헤더:", headers)

    data = []
    for row in table.select("tbody tr"):
        cols = row.select("td")
        values = [col.get_text(strip=True) for col in cols]
        record = dict(zip(headers, values))
        data.append(record)
    # print(data)
    return data

# 실행
# asyncio.run(extract_sector_data())
if __name__ == "__main__":
    result = asyncio.run(extract_sector_data())
    print(json.dumps(result, indent=2))