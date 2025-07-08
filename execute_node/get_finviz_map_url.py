import asyncio
import base64
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 🌐 브라우저 컨텍스트 설정(우회) 
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 1000},
            java_script_enabled=True,
            locale="en-US"
)

        page = await context.new_page()
        await page.goto("https://finviz.com/map.ashx", wait_until="domcontentloaded", timeout=60000)
        
        # 🧭 캔버스의 위치 정보 계산
        box = await page.evaluate("""() => {
            const el = document.querySelector('canvas.chart');
            if (!el) return null;
            const rect = el.getBoundingClientRect();
            return {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height
            };
        }""")

        if not box:
            print("❌ 캔버스 요소를 찾을 수 없습니다.")
            await browser.close()
            return

        # 🎯 특정 위치만 캡처
        image_bytes = await page.screenshot(clip=box)
        base64_img = base64.b64encode(image_bytes).decode("utf-8")
        print(base64_img)

        await browser.close()

asyncio.run(main())
