import streamlit as st
import pandas as pd
import time
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 瀏覽器初始化：專為 Streamlit Cloud 設計 ---
def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=zh-TW")
    
    # 自動偵測 Chromium 二進制檔案路徑
    possible_chrome_paths = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/lib/chromium-browser/chromium"
    ]
    for path in possible_chrome_paths:
        if os.path.exists(path):
            options.binary_location = path
            break

    # 自動偵測 ChromeDriver 路徑
    possible_driver_paths = [
        "/usr/bin/chromedriver",
        "/usr/lib/chromium-browser/chromedriver"
    ]
    driver_path = None
    for path in possible_driver_paths:
        if os.path.exists(path):
            driver_path = path
            break
            
    try:
        if driver_path:
            service = Service(driver_path)
            return webdriver.Chrome(service=service, options=options)
        else:
            # 備用方案：交給 Selenium Manager 自動處理
            return webdriver.Chrome(options=options)
    except Exception as e:
        st.error(f"❌ 瀏覽器啟動失敗：{e}")
        return None

# --- 爬蟲核心邏輯 ---
def scrape_reviews(driver, shop_name, max_count):
    wait = WebDriverWait(driver, 15)
    # 策略：直接搜尋 Google 評論頁面
    driver.get(f"https://www.google.com/search?q={shop_name}+Google+評論")
    time.sleep(3)

    try:
        # 尋找觸發評論彈窗的按鈕
        triggers = [
            "//a[contains(@data-async-trigger, 'review')]",
            "//a[contains(text(), '則評論')]",
            "//span[contains(text(), 'Google 評論')]",
            "//a[contains(@aria-label, '評論')]"
        ]
        
        found = False
        for xpath in triggers:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                btn.click()
                found = True
                break
            except: continue
            
        if not found:
            return None, "找不到評論按鈕，請嘗試更精確的店名。"

        time.sleep(3)
        reviews_list = []
        last_len = 0
        
        # 評論容器
        container_xpath = "//div[contains(@class, 'review-dialog-list') or @role='main']"
        
        status_text = st.empty()
        for i in range(10): # 限制捲動次數防止記憶體溢出
            elements = driver.find_elements(By.XPATH, "//div[@data-review-id] | //div[contains(@class, 'gws-localreviews__google-review')]")
            
            for el in elements[last_len:]:
                try:
                    # 姓名
                    name = el.find_element(By.XPATH, ".//div[contains(@class, 'TS76Pe') or contains(@class, 'd4r55')]").text
                    # 內容
                    try:
                        content = el.find_element(By.XPATH, ".//span[contains(@class, 'review-full-text') or contains(@class, 'wiI7pd')]").text
                    except:
                        content = "(僅評分，無文字內容)"
                    
                    reviews_list.append({"姓名": name, "評論內容": content})
                    if len(reviews_list) >= max_count: break
                except: continue
                
            if len(reviews_list) >= max_count: break
            
            # 捲動
            try:
                scroll_div = driver.find_element(By.XPATH, container_xpath)
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div)
            except:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            time.sleep(2)
            status_text.text(f"⏳ 已收集 {len(reviews_list)} 則評論...")
            if len(elements) == last_len: break
            last_len = len(elements)

        return pd.DataFrame(reviews_list), None

    except Exception as e:
        return None, f"爬取中斷：{str(e)[:100]}..."

# --- Streamlit UI介面 ---
st.set_page_config(page_title="Google Maps Crawler", page_icon="📍")
st.title("📍 Google Maps 評論全自動爬蟲")

with st.sidebar:
    st.header("設定項目")
    target = st.text_input("輸入店家名稱", value="十二段東山店")
    limit = st.slider("抓取數量", 5, 50, 10)
    st.info("提示：如果搜尋不到，請加上縣市名，例如「台中十二段東山店」。")

if st.button("🚀 開始爬取資料", use_container_width=True):
    with st.spinner("正在啟動瀏覽器並搜尋店家..."):
        browser = init_driver()
        if browser:
            df, error = scrape_reviews(browser, target, limit)
            browser.quit()
            
            if error:
                st.error(f"錯誤：{error}")
            elif df is not None:
                st.success(f"✅ 成功抓取 {len(df)} 則評論！")
                st.dataframe(df, use_container_width=True)
                
                # 下載 CSV
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載評論結果", csv, f"{target}.csv", "text/csv")
            else:
                st.warning("查無結果。")
