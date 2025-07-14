import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        page = await context.new_page()

        await page.goto("https://finviz.com/groups.ashx", wait_until="domcontentloaded")
        # await page.goto("https://finviz.com/groups.ashx", wait_until="networkidle") # wait for all network requests to finish
        await page.wait_for_selector("div.futures.pt-2\\.5", timeout=10000)
        html = await page.content()
        await browser.close()
    
    # BeautifulSoup 파싱
    soup = BeautifulSoup(html, "html.parser")

    # 모든 futures 섹션 찾기
    sections = soup.find_all("div", class_=["futures", "pt-2.5"])
    # print(f"🔍 섹션 수: {len(sections)}")

    target_section = None
    for section in sections:
        h1 = section.find("h1")
        if h1 and "1 Day Performance" in h1.text:
            target_section = section
            break

    if not target_section:
        print("❌ 1 Day Performance 섹션을 찾지 못했습니다.")
        return

    # 섹터 데이터 추출
    data = []
    for rect in target_section.select("div.rect"):
        label = rect.select_one("div.label")
        value = rect.select_one("div.value")
        data.append({
            "sector": label.text.strip() if label else None,
            "value": value.text.strip() if value else None
        })

    return data

if __name__ == "__main__":
    result = asyncio.run(main())
    print(json.dumps(result, indent=2))
