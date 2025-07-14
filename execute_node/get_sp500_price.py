import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json

async def sp500_price():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        page = await context.new_page()

        await page.goto("https://kr.investing.com/equities/americas", wait_until="domcontentloaded")
        await page.wait_for_selector("div#index-select", timeout=15000)
        
        # 2️⃣ 지수 드롭다운 열기
        await page.click("div#index-select")
        await asyncio.sleep(1)

        # 3️⃣ S&P 500 항목 클릭
        await page.locator("div.dropdown_noSelect__rU_0Y", has_text="S&P 500").click()
        await asyncio.sleep(2)

        # 페이지 HTML 가져오기
        html = await page.content()
        await browser.close()

    
    soup = BeautifulSoup(html, "html.parser")

    # ✅ 원하는 테이블 영역 지정
    table = soup.select_one("div.dynamic-table-v2_dynamic-table-wrapper__fBEvo")
    rows = table.select("tr.datatable-v2_row__hkEus")

     # ✅ 헤더 고정 방식
    headers = ["종목명", "종가", "고가", "저가", "변동", "변동률", "거래량"]
    data = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 8:
            continue

        # 📌 td[1]~td[7]만 수집 (td[0]=체크박스, td[8]=시간)
        values = [col.get_text(strip=True) for col in cols[1:-1]]
        record = dict(zip(headers, values))
        data.append(record)

    return data

if __name__ == "__main__":
    events = asyncio.run(sp500_price())
    print(json.dumps(events, indent=2, ensure_ascii=False))
