import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
from collections import defaultdict
import re

def parse_company_and_ticker(text):
    """
    '회사명(티커)' 형태의 문자열에서 분리
    예: "EpicQuest Education International(EEIQ)" → ("EpicQuest Education International", "EEIQ")
    """
    match = re.match(r"(.+?)\s*\((.+?)\)", text)
    if match:
        company_name = match.group(1).strip()
        ticker = match.group(2).strip()
        return company_name, ticker
    return text.strip(), None

def clean_prediction_value(text):
    """
    '/  5.57M' → '5.57M'
    """
    return text.replace("/", "").strip()

async def scroll_until_done(page, pause_time=1200, max_scrolls=60, stable_threshold=4):
    """
    실적 캘린더에서 스크롤을 반복하여 모든 데이터가 로딩될 때까지 기다림
    """
    prev_count = 0
    stable_rounds = 0

    for i in range(max_scrolls):
        await page.mouse.wheel(0, 10000)
        await page.wait_for_timeout(pause_time)

        # tbody 아래의 tr 개수 측정
        row_count = await page.evaluate("""
            () => document.querySelectorAll('#earningsCalendarData tbody tr').length
        """)
        print(f"[{i+1}] Row count: {row_count}")

        if row_count == prev_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        if stable_rounds >= stable_threshold:
            print("✅ 더 이상 로딩되는 항목 없음. 스크롤 종료.")
            break

        prev_count = row_count

async def scrape_us_events():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        page = await context.new_page()

        await page.goto("https://kr.investing.com/earnings-calendar/", wait_until="domcontentloaded")
        await page.wait_for_selector("#timeFrame_thisWeek", timeout=5000)

        # 🔄 '이번 주' 버튼 클릭"
        await page.click("#timeFrame_thisWeek")
        await page.wait_for_selector("td.theDay", timeout=7000)

        # ✅ 페이지 끝까지 스크롤해서 전체 데이터 로딩
        await scroll_until_done(page, pause_time=600)
        
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="earningsCalendarData")

    # 항목은 고정이니까 수동으로 기입
    headers = ["회사", "주당순이익", "주당순이익_예측", "매출", "매출_예축", "총 시가"]
    result_by_date = defaultdict(list)
    current_date = None

    for row in table.select("tbody tr"):
        
        # ✅ 날짜 추출은 <tr> 내부의 <td>를 확인해야 함
        td = row.find("td", class_="theDay")
        if td:
            current_date = td.get_text(strip=True)
            continue
        
        # 이벤트 행: <td> 요소들만 있음. Class를 걸러낼 필요가없음

        # ✅ 미국만 필터링(실적 사이트에선 Naming이 다름, ceFlags)
        flag = row.select_one("span.ceFlags")
        if not flag or "USA" not in flag.get("class", []):
            continue
        
        cols = row.select("td")
        # 요소(국가, 시간, 알림) => X
        values = [col.get_text(strip=True) for col in cols][1:-2]

        # 회사, 티커
        company_raw = values[0]
        company_name, ticker = parse_company_and_ticker(company_raw)
        values[0] = company_name

        # / 공백 제거
        values[2] = clean_prediction_value(values[2])
        values[-2] = clean_prediction_value(values[-2])

        # 이벤트 row 처리
        record = dict(zip(headers, values))
        if ticker:
            record["티커"] = ticker
        else:
            record["티커"] = None
        
        if current_date:
            result_by_date[current_date].append(record)
    
    return result_by_date

# 테스트
if __name__ == "__main__":
    events = asyncio.run(scrape_us_events())
    print(json.dumps(events, indent=2, ensure_ascii=False))
