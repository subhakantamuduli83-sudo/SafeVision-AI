import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

driver = webdriver.Chrome(options=chrome_options)

try:
    print("Navigating to http://localhost:8000/ ...")
    driver.get("http://localhost:8000/")
    time.sleep(3) # Wait for initial data & camera feed load

    # 1. Full Dashboard / Detection Feed View
    print("Capturing 1. Full Dashboard & Detection View...")
    driver.save_screenshot("screenshot_1_dashboard_detection.png")

    # Crop or element screenshot of the Live Detection feed specifically
    try:
        video_wrap = driver.find_element(By.ID, "videoWrapper")
        video_wrap.screenshot("screenshot_1_live_detection_feed.png")
        print("Captured screenshot_1_live_detection_feed.png")
    except Exception as e:
        print("Could not capture videoWrapper:", e)

    # 2. Scorecard & Heatmap Modal
    # In index.html, btnOpenScorecard opens scorecardModal which contains both Scorecard & Heatmap!
    print("Opening Scorecard Modal...")
    try:
        btn_score = driver.find_element(By.ID, "btnOpenScorecard")
        driver.execute_script("arguments[0].click();", btn_score)
        time.sleep(1.5)
        
        # Capture full page with modal open
        driver.save_screenshot("screenshot_2_scorecard_modal_full.png")
        
        # Capture the modal dialog itself
        modal_elem = driver.find_element(By.ID, "scorecardModal")
        modal_elem.screenshot("screenshot_2_scorecard_and_heatmap.png")
        print("Captured screenshot_2_scorecard_and_heatmap.png")

        # Also let's capture just the scorecard metrics card and heatmap canvas if possible
        try:
            canvas = driver.find_element(By.ID, "heatmapCanvas")
            canvas.screenshot("screenshot_3_spatial_heatmap.png")
            print("Captured screenshot_3_spatial_heatmap.png")
        except Exception as e:
            print("Could not capture heatmapCanvas:", e)

        # Close scorecard modal
        close_score = driver.find_element(By.ID, "btnCloseScorecard")
        driver.execute_script("arguments[0].click();", close_score)
        time.sleep(1)
    except Exception as e:
        print("Error with scorecard modal:", e)

    # 4. Telegram Alert Modal
    print("Opening Telegram Modal...")
    try:
        btn_tele = driver.find_element(By.ID, "btnTelegramModal")
        driver.execute_script("arguments[0].click();", btn_tele)
        time.sleep(1.5)

        driver.save_screenshot("screenshot_4_telegram_modal_full.png")
        tele_modal = driver.find_element(By.ID, "telegramModal")
        tele_modal.screenshot("screenshot_4_telegram_alert_modal.png")
        print("Captured screenshot_4_telegram_alert_modal.png")

        # Close telegram modal
        close_tele = driver.find_element(By.ID, "btnCloseTelegram")
        driver.execute_script("arguments[0].click();", close_tele)
        time.sleep(1)
    except Exception as e:
        print("Error with telegram modal:", e)

    print("All browser screenshots captured successfully!")

finally:
    driver.quit()
