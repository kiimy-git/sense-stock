import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
from collections import defaultdict

# 중요도 ★ + (중요도 설명)
def extract_star_rating_with_title(td):
    '''
    중요도 ★만 추출(예: ★☆☆, ★★☆, ★★★)
    '''
    full = len(td.find_all("i", class_="grayFullBullishIcon"))
    stars = "★" * full + "☆" * (3 - full)
    # title = td.get("title", "").strip()
    return stars

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
        # print(f"[{i+1}] Row count: {row_count}")

        if row_count == prev_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        if stable_rounds >= stable_threshold:
            # print("✅ 더 이상 로딩되는 항목 없음. 스크롤 종료.")
            break

        prev_count = row_count

async def scrape_us_events():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        page = await context.new_page()

        await page.goto("https://kr.investing.com/economic-calendar/", wait_until="domcontentloaded")
        # 1. 'Today'라는 텍스트를 가진 button 요소를 찾을 때까지 대기
        await page.wait_for_selector("button:has-text('Next Week')", timeout=15000)
        
        # 2. 해당 버튼 클릭
        await page.click("button:has-text('Next Week')")
        await page.wait_for_selector("td.theDay", timeout=7000)

        # ✅ 페이지 끝까지 스크롤해서 전체 데이터 로딩
        await scroll_until_done(page, pause_time=600)
        
        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="economicCalendarData")

    # 항목은 고정이니까 수동으로 기입
    headers = ["시간", "외화", "중요성", "이벤트", "실제", "예측", "이전"]
    result_by_date = defaultdict(list)
    current_date = None

    for row in table.select("tbody tr"):
        
        # ✅ 날짜 추출은 <tr> 내부의 <td>를 확인해야 함
        td = row.find("td", class_="theDay")
        if td:
            current_date = td.get_text(strip=True)
            continue

        # 이벤트 행: class="js-event-item", 이벤트가 아닌것들=날짜
        if "js-event-item" not in row.get("class", []):
            continue
        
        # ✅ 미국만 필터링
        flag = row.select_one("span.ceFlags")
        if not flag or "United_States" not in flag.get("class", []):
            continue
        
        cols = row.select("td")
        # 맨뒤 요소는 알림 생성 => X
        values = [col.get_text(strip=True) for col in cols][:-1]
        
        # ✅ 중요성 td에서 별 + 설명 추출
        importance_td = cols[2]
        importance = extract_star_rating_with_title(importance_td)
        values[2] = importance  # 세 번째 요소 교체

        # 이벤트 row 처리
        record = dict(zip(headers, values))
        
        if current_date:
            result_by_date[current_date].append(record)
    
    return result_by_date

# 테스트
if __name__ == "__main__":
    events = asyncio.run(scrape_us_events())
    print(json.dumps(events, indent=2, ensure_ascii=False))
