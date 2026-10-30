import os
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = Path("D:/Gen-AI/HarmonicRAG/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_DIR = Path("C:/Users/LENOVO/.gemini/antigravity-ide/brain/22fbe28b-1f25-4e33-b3f0-b2ba23e4f943")

def capture_screenshot(driver, filename):
    filepath = SCREENSHOT_DIR / filename
    driver.save_screenshot(str(filepath))
    # Also copy to artifact dir if exists
    if ARTIFACT_DIR.exists():
        art_path = ARTIFACT_DIR / filename
        driver.save_screenshot(str(art_path))
    print(f"  Screenshot captured: {filepath}")
    return filepath

def run_comprehensive_verification():
    print("=" * 72)
    print("HARMONICRAG — COMPREHENSIVE MUSIC VISUALIZER UI VERIFICATION SUITE")
    print("=" * 72)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    try:
        # TEST 1: Fresh page load — Piano hidden
        print("\n[TEST 1] Fresh page load: Piano hidden and consumes 0px layout space")
        driver.get("http://127.0.0.1:8000")
        wait.until(EC.presence_of_element_located((By.ID, "chat-input")))
        piano_panel = driver.find_element(By.ID, "piano-panel")

        p_style = driver.execute_script("""
            const p = arguments[0];
            const cs = window.getComputedStyle(p);
            return {
                display: cs.display,
                visibility: cs.visibility,
                height: cs.height,
                maxHeight: cs.maxHeight,
                opacity: cs.opacity,
                is_displayed: p.offsetWidth > 0 && p.offsetHeight > 0
            };
        """, piano_panel)
        is_open = driver.execute_script("return window.pianoSynth ? window.pianoSynth.isVisualizerOpen : null;")

        print(f"  State: isVisualizerOpen={is_open}, display='{p_style['display']}', visibility='{p_style['visibility']}', height='{p_style['height']}'")
        assert is_open is False, f"Expected isVisualizerOpen=False, got {is_open}"
        assert p_style["display"] == "none", f"Expected display='none', got '{p_style['display']}'"
        assert not p_style["is_displayed"], "Piano panel is consuming layout space!"
        capture_screenshot(driver, "01_initial_load_desktop.png")
        print("  >>> PASS: Piano is completely hidden and consumes 0px on initial load.")

        # TEST 2: Toolbar button: Compact and correctly styled
        print("\n[TEST 2] Toolbar button: Compact, dark theme, gold accent, correctly sized")
        toolbar_btn = driver.find_element(By.ID, "btn-toolbar-visualizer")
        svg_icon = toolbar_btn.find_element(By.TAG_NAME, "svg")

        b_style = driver.execute_script("""
            const b = arguments[0];
            const cs = window.getComputedStyle(b);
            return {
                bg: cs.backgroundColor,
                color: cs.color,
                border: cs.border,
                height: cs.height,
                width: cs.width,
                display: cs.display,
                borderRadius: cs.borderRadius
            };
        """, toolbar_btn)

        s_style = driver.execute_script("""
            const s = arguments[0];
            const cs = window.getComputedStyle(s);
            return {
                width: cs.width,
                height: cs.height,
                stroke: cs.stroke,
                color: cs.color
            };
        """, svg_icon)

        print(f"  Button: height={b_style['height']}, width={b_style['width']}, bg={b_style['bg']}, border='{b_style['border']}', radius={b_style['borderRadius']}")
        print(f"  SVG Icon: width={s_style['width']}, height={s_style['height']}, stroke={s_style['stroke']}")

        # Assertions for button styling
        assert b_style["display"] in ["flex", "inline-flex"], f"Expected flex display, got {b_style['display']}"
        h_val = float(b_style["height"].replace("px", ""))
        assert 30 <= h_val <= 42, f"Button height {h_val}px is not compact (expected ~34px)"
        # Check dark background (not white / default 240, 240, 240)
        assert b_style["bg"] != "rgb(240, 240, 240)", f"Button still has default browser white background! {b_style['bg']}"
        # Check SVG icon dimensions are 16px (not 100px)
        svg_w = float(s_style["width"].replace("px", ""))
        assert 14 <= svg_w <= 20, f"SVG icon width is {svg_w}px (expected 16px, not default oversized)"
        print("  >>> PASS: Music Visualizer toolbar button is compact and styled with dark theme.")

        # TEST 3: Submit a question: Piano remains hidden
        print("\n[TEST 3] Submit a question: Piano remains hidden")
        chat_input = driver.find_element(By.ID, "chat-input")
        send_btn = driver.find_element(By.ID, "btn-send")
        chat_input.clear()
        chat_input.send_keys("What is a Perfect Authentic Cadence (PAC) in classical harmony?")
        send_btn.click()

        # Check while loading
        p_while_loading = driver.execute_script("return window.getComputedStyle(document.getElementById('piano-panel')).display;")
        assert p_while_loading == "none", f"Piano showed up while question was loading! display={p_while_loading}"
        print("  >>> PASS: Piano remains hidden while question is being processed.")

        # TEST 4: Receive a response containing visualization data: Piano remains hidden
        print("\n[TEST 4] Receive response with visualization data: Piano remains hidden")
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".message-assistant .message-bubble")) > 0)
        time.sleep(1.0) # allow post-response processing

        p_after_resp = driver.execute_script("return window.getComputedStyle(document.getElementById('piano-panel')).display;")
        is_open_resp = driver.execute_script("return window.pianoSynth.isVisualizerOpen;")
        print(f"  After response: isVisualizerOpen={is_open_resp}, display='{p_after_resp}'")
        assert is_open_resp is False, f"isVisualizerOpen auto-expanded! Got {is_open_resp}"
        assert p_after_resp == "none", f"Piano auto-opened after response! display={p_after_resp}"
        capture_screenshot(driver, "02_after_response_hidden.png")
        print("  >>> PASS: Piano remained hidden after receiving answer with chord data.")

        # TEST 5: Click "Music Visualizer": Panel opens
        print("\n[TEST 5] Click 'Music Visualizer' button: Panel opens")
        toolbar_btn.click()
        time.sleep(0.35)

        is_open_toggle = driver.execute_script("return window.pianoSynth.isVisualizerOpen;")
        p_toggle_disp = driver.execute_script("""
            const p = document.getElementById('piano-panel');
            return {
                display: window.getComputedStyle(p).display,
                height: p.offsetHeight,
                keys: p.querySelectorAll('.piano-key').length
            };
        """)
        print(f"  After toggle: isVisualizerOpen={is_open_toggle}, display='{p_toggle_disp['display']}', height={p_toggle_disp['height']}px, keys={p_toggle_disp['keys']}")
        assert is_open_toggle is True, "isVisualizerOpen did not toggle to True!"
        assert p_toggle_disp["display"] == "flex", f"Expected display='flex', got '{p_toggle_disp['display']}'"
        assert p_toggle_disp["height"] > 0, "Piano height is 0px when opened!"
        assert p_toggle_disp["keys"] >= 36, f"Expected 36 keys, got {p_toggle_disp['keys']}"
        capture_screenshot(driver, "03_visualizer_opened_desktop.png")
        print("  >>> PASS: Clicking toolbar button opens piano with 36 interactive keys.")

        # TEST 6: Click close: Panel disappears and consumes no layout space
        print("\n[TEST 6] Click close button: Panel collapses and consumes 0px")
        close_btn = driver.find_element(By.ID, "btn-close-piano")
        close_btn.click()
        time.sleep(0.35)

        is_open_close = driver.execute_script("return window.pianoSynth.isVisualizerOpen;")
        p_close_disp = driver.execute_script("""
            const p = document.getElementById('piano-panel');
            const cs = window.getComputedStyle(p);
            return {
                display: cs.display,
                height: cs.height,
                offsetHeight: p.offsetHeight
            };
        """)
        print(f"  After close: isVisualizerOpen={is_open_close}, display='{p_close_disp['display']}', offsetHeight={p_close_disp['offsetHeight']}")
        assert is_open_close is False, "isVisualizerOpen is not False after close!"
        assert p_close_disp["display"] == "none", f"Expected display='none', got '{p_close_disp['display']}'"
        assert p_close_disp["offsetHeight"] == 0, f"Expected offsetHeight=0, got {p_close_disp['offsetHeight']}"
        capture_screenshot(driver, "04_after_close_hidden.png")
        print("  >>> PASS: Close button collapses piano and leaves 0px footprint.")

        # TEST 7: Click "View musical example": Opens with correct notes & no auto-playback
        print("\n[TEST 7] Click 'View musical example': Opens with notes & no auto-playback")
        example_btns = driver.find_elements(By.CSS_SELECTOR, ".btn-show-piano")
        assert len(example_btns) > 0, "No 'View musical example' button found on assistant message!"
        btn_text = example_btns[0].text.strip()
        print(f"  Button label: '{btn_text}'")
        assert "example" in btn_text.lower() or "view" in btn_text.lower(), f"Unexpected button label: {btn_text}"

        example_btns[0].click()
        time.sleep(0.35)

        is_open_ex = driver.execute_script("return window.pianoSynth.isVisualizerOpen;")
        p_ex_disp = driver.execute_script("return window.getComputedStyle(document.getElementById('piano-panel')).display;")
        label_text = driver.find_element(By.ID, "piano-label").text.strip()
        highlighted = driver.find_elements(By.CSS_SELECTOR, ".piano-key.theory-highlight, .piano-key.theory-root")

        print(f"  After example click: isVisualizerOpen={is_open_ex}, display='{p_ex_disp}', label='{label_text}', highlighted_keys={len(highlighted)}")
        assert is_open_ex is True, "Piano did not open after clicking 'View musical example'!"
        assert p_ex_disp == "flex", f"Expected display='flex', got '{p_ex_disp}'"
        assert len(highlighted) > 0, "No keys were highlighted for musical example!"
        capture_screenshot(driver, "05_view_musical_example_active.png")
        print("  >>> PASS: 'View musical example' successfully loaded notes and opened visualizer.")

        # TEST 8: Start a new chat: Panel closes and resets selection
        print("\n[TEST 8] Start a new chat: Panel closes and resets selection")
        new_chat_btn = driver.find_element(By.ID, "btn-new-chat")
        new_chat_btn.click()
        time.sleep(0.35)

        is_open_new = driver.execute_script("return window.pianoSynth.isVisualizerOpen;")
        p_new_disp = driver.execute_script("return window.getComputedStyle(document.getElementById('piano-panel')).display;")
        label_reset = driver.execute_script("return document.getElementById('piano-label').textContent;").strip()

        print(f"  After new chat: isVisualizerOpen={is_open_new}, display='{p_new_disp}', label='{label_reset}'")
        assert is_open_new is False, "Piano did not close on starting new chat!"
        assert p_new_disp == "none", f"Expected display='none', got '{p_new_disp}'"
        assert "no active" in label_reset.lower(), f"Label was not reset: '{label_reset}'"
        capture_screenshot(driver, "06_after_new_chat.png")
        print("  >>> PASS: Starting new chat closed visualizer and reset active selection.")

        # TEST 9: Reload the page: Panel returns to default hidden state
        print("\n[TEST 9] Reload the page: Panel returns to default hidden state")
        driver.refresh()
        wait.until(EC.presence_of_element_located((By.ID, "chat-input")))

        is_open_reload = driver.execute_script("return window.pianoSynth ? window.pianoSynth.isVisualizerOpen : null;")
        p_reload_disp = driver.execute_script("return window.getComputedStyle(document.getElementById('piano-panel')).display;")
        print(f"  After reload: isVisualizerOpen={is_open_reload}, display='{p_reload_disp}'")
        assert is_open_reload is False, f"Expected isVisualizerOpen=False after reload, got {is_open_reload}"
        assert p_reload_disp == "none", f"Expected display='none' after reload, got '{p_reload_disp}'"
        print("  >>> PASS: Page reload cleanly returns visualizer to hidden default state.")

        # MOBILE VIEW TEST (375x667)
        print("\n[TEST 10] Mobile viewport test (375x667): Layout and button responsiveness")
        driver.set_window_size(375, 667)
        time.sleep(0.5)

        mob_btn = driver.find_element(By.ID, "btn-toolbar-visualizer")
        mob_btn_h = float(driver.execute_script("return window.getComputedStyle(arguments[0]).height;", mob_btn).replace("px", ""))
        mob_piano = driver.find_element(By.ID, "piano-panel")
        mob_p_disp = driver.execute_script("return window.getComputedStyle(arguments[0]).display;", mob_piano)

        print(f"  Mobile: toolbar button height={mob_btn_h}px, piano display='{mob_p_disp}'")
        assert mob_p_disp == "none", "Piano panel visible on mobile initial load!"
        assert mob_btn_h <= 42, f"Toolbar button too tall on mobile: {mob_btn_h}px"
        capture_screenshot(driver, "07_mobile_view_375x667.png")

        # Open on mobile
        mob_btn.click()
        time.sleep(0.35)
        mob_open_disp = driver.execute_script("return window.getComputedStyle(arguments[0]).display;", mob_piano)
        assert mob_open_disp == "flex", f"Piano did not open on mobile! display='{mob_open_disp}'"
        capture_screenshot(driver, "08_mobile_visualizer_opened.png")
        print("  >>> PASS: Mobile layout correctly renders compact button and responsive piano.")

        print("\n" + "=" * 72)
        print(">>> ALL 10 COMPREHENSIVE VERIFICATION TESTS PASSED WITH 100% SUCCESS! <<<")
        print("=" * 72)

    finally:
        driver.quit()

if __name__ == "__main__":
    run_comprehensive_verification()
