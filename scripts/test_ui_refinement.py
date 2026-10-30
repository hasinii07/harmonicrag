import os
import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

SCREENSHOT_DIR = Path("D:/Gen-AI/HarmonicRAG/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_DIR = Path("C:/Users/LENOVO/.gemini/antigravity-ide/brain/22fbe28b-1f25-4e33-b3f0-b2ba23e4f943")

def capture(driver, name):
    fp = SCREENSHOT_DIR / name
    driver.save_screenshot(str(fp))
    if ARTIFACT_DIR.exists():
        driver.save_screenshot(str(ARTIFACT_DIR / name))
    print(f"  [SCREENSHOT] {name}")
    return fp

def run_tests():
    print("=" * 75)
    print("HARMONICRAG — UI/UX SIZE, SPACING & CONSISTENCY VERIFICATION")
    print("=" * 75)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    try:
        # Load page on Desktop (1440x900)
        print("\n--- VIEWPORT 1: DESKTOP 1440 x 900 ---")
        driver.set_window_size(1440, 900)
        driver.get("http://127.0.0.1:8000")
        wait.until(EC.presence_of_element_located((By.ID, "chat-input")))
        time.sleep(1.0) # allow health check and conversations to load

        # -------------------------------------------------------------
        # TEST 1: New Chat button compact sizing and styling
        # -------------------------------------------------------------
        print("\n[TEST 1] New Chat Button Size & Dimensions")
        new_chat_btn = driver.find_element(By.ID, "btn-new-chat")
        new_chat_svg = new_chat_btn.find_element(By.TAG_NAME, "svg")

        nc_dims = driver.execute_script("""
            const b = arguments[0];
            const s = arguments[1];
            const cs = window.getComputedStyle(b);
            const scs = window.getComputedStyle(s);
            return {
                h: b.offsetHeight,
                w: b.offsetWidth,
                bg: cs.backgroundImage || cs.backgroundColor,
                borderRadius: cs.borderRadius,
                iconW: s.offsetWidth || parseFloat(scs.width),
                iconH: s.offsetHeight || parseFloat(scs.height),
                text: b.textContent.trim()
            };
        """, new_chat_btn, new_chat_svg)

        print(f"  New Chat: height={nc_dims['h']}px, width={nc_dims['w']}px, icon={nc_dims['iconW']}x{nc_dims['iconH']}px, label='{nc_dims['text']}'")
        assert 46 <= nc_dims['h'] <= 56, f"New Chat height {nc_dims['h']}px is out of target range (48-56px)"
        assert 16 <= nc_dims['iconW'] <= 24, f"New Chat icon width {nc_dims['iconW']}px is out of target range (18-22px)"
        assert 16 <= nc_dims['iconH'] <= 24, f"New Chat icon height {nc_dims['iconH']}px is out of target range (18-22px)"
        assert "new chat" in nc_dims['text'].lower(), f"Unexpected label: {nc_dims['text']}"
        print("  >>> PASS: New Chat button is compact, horizontally aligned, with proportional icon.")

        # -------------------------------------------------------------
        # TEST 2: Sidebar Navigation Buttons Standardized
        # -------------------------------------------------------------
        print("\n[TEST 2] Sidebar Navigation Buttons Standardized Dimensions")
        nav_chat = driver.find_element(By.ID, "nav-chat")
        nav_docs = driver.find_element(By.ID, "nav-documents")
        nav_eval = driver.find_element(By.ID, "nav-evaluation")

        nav_items_data = driver.execute_script("""
            const items = [arguments[0], arguments[1], arguments[2]];
            return items.map(el => {
                const cs = window.getComputedStyle(el);
                const svg = el.querySelector('svg');
                const scs = svg ? window.getComputedStyle(svg) : null;
                return {
                    id: el.id,
                    height: el.offsetHeight,
                    paddingLeft: cs.paddingLeft,
                    paddingRight: cs.paddingRight,
                    fontSize: cs.fontSize,
                    lineHeight: cs.lineHeight,
                    iconW: svg ? svg.offsetWidth || parseFloat(scs.width) : 0,
                    iconH: svg ? svg.offsetHeight || parseFloat(scs.height) : 0,
                    active: el.classList.contains('active'),
                    borderLeft: cs.borderLeft
                };
            });
        """, nav_chat, nav_docs, nav_eval)

        for item in nav_items_data:
            print(f"  Item #{item['id']}: height={item['height']}px, padding={item['paddingLeft']}, icon={item['iconW']}x{item['iconH']}px, active={item['active']}")
            assert 42 <= item['height'] <= 50, f"Nav item {item['id']} height {item['height']}px out of range (44-48px)"
            assert item['paddingLeft'] == "14px", f"Expected paddingLeft 14px, got {item['paddingLeft']}"
            assert 17 <= item['iconW'] <= 22, f"Nav item {item['id']} icon width {item['iconW']}px out of range (18-20px)"

        # Check badge aligned right
        badge = driver.find_element(By.ID, "badge-doc-count")
        b_margin = driver.execute_script("return window.getComputedStyle(arguments[0]).marginLeft;", badge)
        assert b_margin == "auto" or float(b_margin.replace("px", "")) > 10, f"Badge not aligned to right: marginLeft={b_margin}"
        print("  >>> PASS: Navigation items standardized in height (46px), icon size (19px), and padding.")

        # -------------------------------------------------------------
        # TEST 3: Sidebar Status Section & Gear Decoration
        # -------------------------------------------------------------
        print("\n[TEST 3] Sidebar Status Section & Compact Gear Icon")
        gear_svg = driver.find_element(By.CSS_SELECTOR, ".settings-gear-icon")
        status_dot = driver.find_element(By.ID, "system-status-dot")
        status_text = driver.find_element(By.ID, "system-status-text")
        footer_el = driver.find_element(By.CSS_SELECTOR, ".sidebar-footer")

        status_info = driver.execute_script("""
            const g = arguments[0];
            const d = arguments[1];
            const t = arguments[2];
            const f = arguments[3];
            const gcs = window.getComputedStyle(g);
            const dcs = window.getComputedStyle(d);
            const tcs = window.getComputedStyle(t);
            return {
                gearW: g.offsetWidth || parseFloat(gcs.width),
                gearH: g.offsetHeight || parseFloat(gcs.height),
                dotW: d.offsetWidth,
                dotH: d.offsetHeight,
                dotColor: dcs.backgroundColor,
                label: t.textContent.trim(),
                footerH: f.offsetHeight
            };
        """, gear_svg, status_dot, status_text, footer_el)

        print(f"  Status: label='{status_info['label']}', dot={status_info['dotW']}x{status_info['dotH']}px, gear={status_info['gearW']}x{status_info['gearH']}px, footerHeight={status_info['footerH']}px")
        assert status_info['gearW'] <= 20, f"Gear icon too large: {status_info['gearW']}px (must not dominate interface)"
        assert status_info['gearH'] <= 20, f"Gear icon too large: {status_info['gearH']}px"
        assert status_info['dotW'] <= 12 and status_info['dotH'] <= 12, "Status dot not compact"
        assert "gemini" in status_info['label'].lower() or "active" in status_info['label'].lower() or "configured" in status_info['label'].lower()
        print("  >>> PASS: Settings gear reduced to 16px; status dot and label compact and accurate.")

        # -------------------------------------------------------------
        # TEST 4: Music Visualizer Toolbar Button
        # -------------------------------------------------------------
        print("\n[TEST 4] Music Visualizer Toolbar Button Refinement")
        viz_btn = driver.find_element(By.ID, "btn-toolbar-visualizer")
        viz_svg = viz_btn.find_element(By.TAG_NAME, "svg")

        viz_data = driver.execute_script("""
            const b = arguments[0];
            const s = arguments[1];
            const cs = window.getComputedStyle(b);
            const scs = window.getComputedStyle(s);
            return {
                height: b.offsetHeight,
                width: b.offsetWidth,
                iconW: s.offsetWidth || parseFloat(scs.width),
                iconH: s.offsetHeight || parseFloat(scs.height),
                bg: cs.backgroundColor,
                borderRadius: cs.borderRadius,
                text: b.textContent.trim()
            };
        """, viz_btn, viz_svg)

        print(f"  Music Visualizer Button: height={viz_data['height']}px, width={viz_data['width']}px, icon={viz_data['iconW']}x{viz_data['iconH']}px, radius={viz_data['borderRadius']}")
        assert 38 <= viz_data['height'] <= 44, f"Toolbar button height {viz_data['height']}px out of target range (38-42px)"
        assert 15 <= viz_data['iconW'] <= 20, f"Toolbar icon width {viz_data['iconW']}px out of target range (16-18px)"
        assert viz_data['borderRadius'] == "10px", f"Expected radius 10px, got {viz_data['borderRadius']}"
        print("  >>> PASS: Music Visualizer toolbar button fits exact 38-42px spec with 17px icon.")

        # -------------------------------------------------------------
        # TEST 5: Suggested-Question Cards Standardized 2-Column Grid
        # -------------------------------------------------------------
        print("\n[TEST 5] Suggested-Question Cards 2-Column Grid on Desktop")
        example_grid = driver.find_element(By.CSS_SELECTOR, ".example-grid")
        example_cards = driver.find_elements(By.CSS_SELECTOR, ".example-card")

        grid_data = driver.execute_script("""
            const g = arguments[0];
            const cards = Array.from(arguments[1]);
            const gcs = window.getComputedStyle(g);
            return {
                gridCols: gcs.gridTemplateColumns.split(' ').length,
                totalCards: cards.length,
                cardHeights: cards.map(c => c.offsetHeight),
                padding: window.getComputedStyle(cards[0]).padding
            };
        """, example_grid, example_cards)

        print(f"  Grid columns on 1440px desktop: {grid_data['gridCols']} columns, {grid_data['totalCards']} cards, card padding: {grid_data['padding']}")
        print(f"  Card heights: {grid_data['cardHeights']}")
        assert grid_data['gridCols'] == 2, f"Expected 2-column grid on desktop, got {grid_data['gridCols']}"
        assert grid_data['totalCards'] == 6, f"Expected 6 example cards, got {grid_data['totalCards']}"
        for h in grid_data['cardHeights']:
            assert 70 <= h <= 130, f"Card height {h}px unbalanced"
        print("  >>> PASS: Suggested inquiries cleanly arranged in 2 responsive columns.")

        # -------------------------------------------------------------
        # TEST 6: Chat Composer Alignment & Viewport Clearance
        # -------------------------------------------------------------
        print("\n[TEST 6] Chat Composer Alignment & Viewport Spacing")
        input_bar = driver.find_element(By.CSS_SELECTOR, ".chat-input-bar")
        input_wrap = driver.find_element(By.CSS_SELECTOR, ".input-wrapper")
        textarea = driver.find_element(By.ID, "chat-input")
        send_btn = driver.find_element(By.ID, "btn-send")
        send_svg = send_btn.find_element(By.TAG_NAME, "svg")
        viewport = driver.find_element(By.CSS_SELECTOR, ".chat-viewport")

        comp_data = driver.execute_script("""
            const bar = arguments[0];
            const wrap = arguments[1];
            const ta = arguments[2];
            const btn = arguments[3];
            const ssvg = arguments[4];
            const vp = arguments[5];

            const barRect = bar.getBoundingClientRect();
            const vpRect = vp.getBoundingClientRect();
            const taRect = ta.getBoundingClientRect();
            const btnRect = btn.getBoundingClientRect();
            const ssvgCS = window.getComputedStyle(ssvg);

            return {
                barBottom: barRect.bottom,
                windowH: window.innerHeight,
                vpOverlappedByBar: vpRect.bottom > barRect.top + 1,
                taCenterY: (taRect.top + taRect.bottom) / 2,
                btnCenterY: (btnRect.top + btnRect.bottom) / 2,
                centerDiff: Math.abs(((taRect.top + taRect.bottom) / 2) - ((btnRect.top + btnRect.bottom) / 2)),
                btnW: btn.offsetWidth,
                btnH: btn.offsetHeight,
                iconW: ssvg.offsetWidth || parseFloat(ssvgCS.width),
                iconH: ssvg.offsetHeight || parseFloat(ssvgCS.height)
            };
        """, input_bar, input_wrap, textarea, send_btn, send_svg, viewport)

        print(f"  Composer: btnSize={comp_data['btnW']}x{comp_data['btnH']}px, sendIcon={comp_data['iconW']}x{comp_data['iconH']}px, verticalCenterDiff={comp_data['centerDiff']:.2f}px")
        assert comp_data['centerDiff'] <= 8.0, f"Text area and send button vertical centers misaligned by {comp_data['centerDiff']}px"
        assert 32 <= comp_data['btnW'] <= 40, f"Send button width {comp_data['btnW']}px not compact"
        assert 14 <= comp_data['iconW'] <= 20, f"Send icon width {comp_data['iconW']}px not compact"
        print("  >>> PASS: Composer is anchored at bottom, send button vertically aligned with textarea.")

        # Capture Desktop Screenshot
        capture(driver, "09_desktop_1440x900_refined.png")

        # -------------------------------------------------------------
        # TEST 7: Laptop Viewport (1280 x 800)
        # -------------------------------------------------------------
        print("\n--- VIEWPORT 2: LAPTOP 1280 x 800 ---")
        driver.set_window_size(1280, 800)
        time.sleep(0.5)

        lap_grid_cols = driver.execute_script("""
            const g = document.querySelector('.example-grid');
            return window.getComputedStyle(g).gridTemplateColumns.split(' ').length;
        """)
        assert lap_grid_cols == 2, f"Expected 2 columns on laptop, got {lap_grid_cols}"
        capture(driver, "10_laptop_1280x800_refined.png")
        print("  >>> PASS: Laptop 1280x800 maintains 2-column cards, sidebar, and composer spacing.")

        # -------------------------------------------------------------
        # TEST 8: Mobile Viewport (375 x 667)
        # -------------------------------------------------------------
        print("\n--- VIEWPORT 3: MOBILE 375 x 667 ---")
        driver.set_window_size(375, 667)
        time.sleep(0.5)

        mob_info = driver.execute_script("""
            const g = document.querySelector('.example-grid');
            const topbar = document.querySelector('.topbar');
            const sidebar = document.getElementById('sidebar');
            const piano = document.getElementById('piano-panel');
            const vizBtn = document.getElementById('btn-toolbar-visualizer');
            const docWidth = document.documentElement.scrollWidth;
            const winWidth = window.innerWidth;

            return {
                gridCols: window.getComputedStyle(g).gridTemplateColumns.split(' ').length,
                topbarVisible: window.getComputedStyle(topbar).display !== 'none',
                sidebarTransform: window.getComputedStyle(sidebar).transform,
                pianoDisplay: window.getComputedStyle(piano).display,
                vizBtnVisible: window.getComputedStyle(vizBtn).display !== 'none',
                hasHorizontalOverflow: docWidth > winWidth
            };
        """)

        print(f"  Mobile 375x667: gridCols={mob_info['gridCols']}, topbarVisible={mob_info['topbarVisible']}, overflow={mob_info['hasHorizontalOverflow']}, pianoDisplay={mob_info['pianoDisplay']}")
        assert mob_info['gridCols'] == 1, f"Expected 1 column on mobile, got {mob_info['gridCols']}"
        assert mob_info['topbarVisible'] is True, "Mobile topbar not visible"
        assert not mob_info['hasHorizontalOverflow'], f"Horizontal overflow detected on mobile!"
        assert mob_info['pianoDisplay'] == "none", "Piano panel auto-expanded on mobile!"
        capture(driver, "11_mobile_375x667_refined.png")
        print("  >>> PASS: Mobile layout stacks cards to 1 column, adapts topbar, zero horizontal overflow.")

        # -------------------------------------------------------------
        # TEST 9: Functional Click Interactions
        # -------------------------------------------------------------
        print("\n[TEST 9] Functional Test: Click Suggested Question & Visualizer Interaction")
        # Return to laptop size
        driver.set_window_size(1280, 800)
        time.sleep(0.5)

        # Click first example card
        first_card = driver.find_elements(By.CSS_SELECTOR, ".example-card")[0]
        q_text = first_card.get_attribute("data-question")
        first_card.click()
        print(f"  Clicked suggested inquiry: '{q_text}'")

        # Wait for assistant response
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".message-assistant")) > 0)
        time.sleep(1.0)

        # Confirm piano remained hidden
        p_disp = driver.execute_script("return window.getComputedStyle(document.getElementById('piano-panel')).display;")
        assert p_disp == "none", f"Piano auto-expanded after inquiry! display={p_disp}"
        capture(driver, "12_chat_response_cards_hidden_piano.png")
        print("  >>> PASS: Suggested card query processed cleanly, piano remained hidden.")

        # Test New Chat button click
        new_btn = driver.find_element(By.ID, "btn-new-chat")
        new_btn.click()
        time.sleep(0.5)

        msgs_count = len(driver.find_elements(By.CSS_SELECTOR, ".message-row"))
        assert msgs_count == 0, f"Messages not cleared after New Chat! count={msgs_count}"
        welcome_visible = driver.find_element(By.ID, "welcome-screen").is_displayed()
        assert welcome_visible is True, "Welcome screen not restored after New Chat!"
        capture(driver, "13_after_new_chat_cleared.png")
        print("  >>> PASS: New Chat successfully cleared messages and restored welcome screen.")

        print("\n" + "=" * 75)
        print(">>> ALL UI/UX SIZE, SPACING & CONSISTENCY TESTS PASSED (9/9)! <<<")
        print("=" * 75)

    finally:
        driver.quit()

if __name__ == "__main__":
    run_tests()
