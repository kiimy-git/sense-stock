import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json

async def sp500_perf():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        page = await context.new_page()

        await page.goto("https://kr.investing.com/equities/americas", wait_until="domcontentloaded")
        await page.wait_for_selector("div#index-select", timeout=15000)
        
        # 2️⃣ 지수 드롭다운 열기
        await page.click("div#index-select")
        await asyncio.sleep(1)

        # # 2️⃣ 팝업 외부 클릭 → 예: 배경 어딘가 클릭해서 닫기 / 조금이라도 클릭시간이 지체되면 로그인창 뜸
        # await page.mouse.click(10, 10)  # 좌측 상단 모서리 클릭
        # await asyncio.sleep(1)

        # 3️⃣ S&P 500 항목 클릭
        await page.locator("div.dropdown_noSelect__rU_0Y", has_text="S&P 500").click()
        await asyncio.sleep(1)

        # 성과 클릭
        await page.click('button[data-test="quote-tab"][data-test-tab-id="1"]')
        await asyncio.sleep(2)

        # 페이지 HTML 가져오기
        html = await page.content()
        await browser.close()

    
    soup = BeautifulSoup(html, "html.parser")

    # ✅ 원하는 테이블 영역 지정
    tbody = soup.select_one("tbody.datatable-v2_body__8TXQk")
    rows = tbody.select("tr.datatable-v2_row__hkEus.dynamic-table-v2_row__ILVMx")


     # ✅ 헤더 고정 방식
    headers = ["종목명", "일간", "주간", "월간", "YTD", "1년", "3년"]
    data = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 8:
            continue

        # 📌 td[0] 제외, td[0]=체크박스
        values = [col.get_text(strip=True) for col in cols[1:]]
        record = dict(zip(headers, values))
        data.append(record)
    
    # print(len(data))
    return data

if __name__ == "__main__":
    events = asyncio.run(sp500_perf())
    print(json.dumps(events, indent=2, ensure_ascii=False))
