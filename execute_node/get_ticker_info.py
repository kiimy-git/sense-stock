import asyncio
import sys
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json

async def extract_stock_info(ticker):
    url = f"https://finviz.com/screener.ashx?v=111&t={ticker}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")

        ## 렌더링 타이밍 문제를 확실히 잡기 위해서
        await page.wait_for_selector("table.screener_table", timeout=10000)

        html = await page.content()
        await browser.close()
    
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.screener_table")
    if not table:
        print("❌ 테이블을 찾지 못했습니다.")
        return None

    # 항목 추출
    headers = [th.get_text(strip=True) for th in table.select("thead th")]

    # 항목별 값 추출
    row = table.find("tr", class_=lambda c: c and "styled-row" in c)
    values = [td.get_text(strip=True) for td in row.select("td")]

    result = dict(zip(headers, values))
    return result

# 실행 예시
if __name__ == "__main__":
    ticker = sys.argv[1]  # CLI 인자에서 ticker 받아오기
    result = asyncio.run(extract_stock_info(ticker))
    print(json.dumps(result))  # 👉 stdout에 JSON 출력 (n8n에서 받을 수 있게)
