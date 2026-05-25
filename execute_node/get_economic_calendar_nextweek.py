import asyncio
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup
import json
from collections import defaultdict

def extract_star_rating_from_svg(cell):
    """새로운 구조에서 SVG 투명도를 기준으로 별점을 추출합니다."""
    svgs = cell.find_all("svg")
    if not svgs:
        return ""
    full_stars = 0
    for svg in svgs:
        svg_class = svg.get("class", [])
        if not any("opacity-20" in c for c in svg_class):
            full_stars += 1
    return "★" * full_stars + "☆" * (len(svgs) - full_stars)

async def scroll_until_done(page, pause_time=1000, max_scrolls=100, stable_threshold=5):
    """
    스크롤을 내리다가 '더 보기' 버튼이 나타나면 클릭하며 
    더 이상 데이터가 늘어나지 않을 때까지 끝까지 내려가는 로직
    """
    prev_count = 0
    stable_rounds = 0

    # 인베스팅닷컴의 '더 보기' 관련 예상 선택자 리스트 (텍스트 매칭 포함)
    show_more_selector = "button:has-text('더 보기'), a:has-text('더 보기'), [class*='showMore'], [id*='showMore']"

    for i in range(max_scrolls):
        # 1. 휠을 조금씩 끊어서 스크롤 다운
        for _ in range(3):
            await page.mouse.wheel(0, 1500)
            await page.wait_for_timeout(200)
            
        await page.wait_for_timeout(pause_time)

        # ⚡ 2. '더 보기' 버튼이 노출되었는지 확인하고 있으면 클릭
        try:
            # 버튼이 화면에 존재하고 클릭 가능한 상태인지 체크
            show_more_btn = page.locator(show_more_selector).first
            if await show_more_btn.is_visible() and await show_more_btn.is_enabled():
                print("🔘 '더 보기' 버튼 발견! 클릭합니다.")
                await show_more_btn.click()
                await page.wait_for_timeout(1500) # 버튼 클릭 후 로딩 시간 확보
        except Exception:
            pass # 버튼이 없는 스크롤 루프 회차는 그냥 통과

        # 3. 현재까지 로드된 행 개수 측정
        row_count = await page.evaluate("""
            () => document.querySelectorAll("tbody[class*='datatable-v2_body'] tr[class*='datatable-v2_row']").length
        """)
        
        print(f"🔄 스크롤 [{i+1}/{max_scrolls}] - 현재 로드된 전체 행 개수: {row_count}")

        # 4. 데이터가 더 이상 늘어나지 않는지 체크 (종료 조건)
        if row_count == prev_count:
            stable_rounds += 1
            if stable_rounds >= stable_threshold:
                print("✅ 더 이상 새로운 데이터가 없습니다. 최종 스크롤을 종료합니다.")
                break
        else:
            stable_rounds = 0

        prev_count = row_count

async def scrape_us_events():
    async with async_playwright() as p:
        # 눈으로 더보기 클릭과 스크롤 진행 상황을 볼 수 있도록 설정
        browser = await p.chromium.launch(headless=True, slow_mo=500)
        context = await browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("🌐 인베스팅닷컴 접속 중...")
        await page.goto("https://kr.investing.com/economic-calendar/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        # '다음 주' 버튼 클릭
        next_week_selector = "button:has(span:text('다음 주'))"
        await page.wait_for_selector(next_week_selector, timeout=15000)
        await page.click(next_week_selector)
        print("✅ '다음 주' 버튼 클릭 완료.")
        
        try:
            await page.wait_for_selector("tr[class*='datatable-v2_row']", timeout=15000)
        except TimeoutError:
            print("🚨 데이터를 로드하지 못했습니다.")
            await browser.close()
            return {}

        # 데이터 끝까지 스크롤 수행 (더보기 클릭 병행)
        print("⏳ 데이터 스크롤 및 더보기 탐색 시작...")
        await scroll_until_done(page, pause_time=1200)
        
        html = await page.content()
        await browser.close()

    # ==============================================================
    # BeautifulSoup 파싱 및 미국 데이터 필터링 로직
    # ==============================================================
    soup = BeautifulSoup(html, "html.parser")
    tbody = soup.select_one("tbody[class*='datatable-v2_body']")

    if not tbody:
        print("🚨 테이블 본문을 찾지 못했습니다.")
        return {}

    headers = ["시간", "외화", "중요성", "이벤트", "실제", "예측", "이전"]
    result_by_date = defaultdict(list)
    current_date = None

    for row in tbody.find_all("tr", class_="datatable-v2_row__hkEus"):
        # 날짜 행 확인
        date_div = row.find("div", class_="font-semibold")
        if date_div and "년" in date_div.get_text():
            current_date = date_div.get_text(strip=True)
            continue

        if not row.has_attr("id"):
            continue

        cells = row.find_all("td")
        if len(cells) < 8:
            continue
        
        # 전체 데이터 중에서 오직 미국 데이터만 필터링하여 수집
        us_flag = row.find(attrs={"data-test": "flag-US"})
        if not us_flag:
            continue
        
        try:
            time = cells[1].get_text(strip=True)
            currency = cells[2].get_text(strip=True)
            event_name = cells[3].get_text(strip=True)
            importance = extract_star_rating_from_svg(cells[4])
            actual = cells[5].get_text(strip=True)
            forecast = cells[6].get_text(strip=True)
            previous = cells[7].get_text(strip=True)

            actual = actual if actual else "-"
            forecast = forecast if forecast else "-"
            previous = previous if previous else "-"

            record = dict(zip(headers, [time, currency, importance, event_name, actual, forecast, previous]))
            
            if current_date:
                result_by_date[current_date].append(record)
                
        except IndexError:
            continue

    return result_by_date

if __name__ == "__main__":
    events = asyncio.run(scrape_us_events())
    print("\n🎉 전체 데이터 수집 및 미국 필터링 파싱 완료!")
    print(json.dumps(events, indent=2, ensure_ascii=False))