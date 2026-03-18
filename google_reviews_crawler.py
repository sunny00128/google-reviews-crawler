import time
import csv
import re
import os
import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- 設定 ---
SEARCH_QUERY = "十二段東山店"
MAX_SCROLLS = 10  # 測試建議先設 10，正式抓取再調高

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new") # 雲端執行必須無頭模式
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=zh-TW")

    # 檢查是否在 Streamlit Cloud (Linux) 環境
    if os.path.exists("/usr/bin/chromedriver"):
        service = Service("/usr/bin/chromedriver")
    else:
        # 本地開發環境使用 webdriver-manager
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def scrape_google_reviews(driver, query):
    wait = WebDriverWait(driver, 20)
    # 1. 前往 Google Maps
    driver.get(f"https://www.google.com/maps/search/{query}")
    time.sleep(5)

    # 2. 點擊評論分頁 (使用更穩健的 XPATH)
    try:
        reviews_tab = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(@aria-label, '評論') or .//div[contains(text(),'評論')]]")
        ))
        reviews_tab.click()
        time.sleep(3)
    except Exception as e:
        st.error(f"找不到評論分頁：{e}")
        return []

    # 3. 滾動加載
    try:
        scrollable_div = driver.find_element(By.XPATH, "//div[@role='main' or @role='feed' or contains(@class, 'm67q60')]")
        for i in range(MAX_SCROLLS):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(2)
            st.write(f"⏳ 正在捲動載入評論... ({i+1}/{MAX_SCROLLS})")
    except:
        st.warning("無法捲動，將嘗試抓取目前內容。")

    # 4. 解析評論
    reviews_data = []
    items = driver.find_elements(By.XPATH, "//div[@data-review-id]")
    
    for item in items:
        try:
            # 展開全文
            try:
                more_btn = item.find_element(By.XPATH, ".//button[contains(text(), '全文') or contains(text(), 'More')]")
                driver.execute_script("arguments[0].click();", more_btn)
            except: pass

            name = item.find_element(By.CLASS_NAME, "d4r55").text
            rating_str = item.find_element(By.XPATH, ".//span[@role='img']").get_attribute("aria-label")
            rating = re.search(r"\d", rating_str).group() if rating_str else "N/A"
            date = item.find_element(By.CLASS_NAME, "rsqaWe").text
            content = item.find_element(By.CLASS_NAME, "wiI7pd").text
            
            reviews_data.append({"姓名": name, "星級": rating, "日期": date, "評論內容": content})
        except:
            continue
            
    return reviews_data

# --- Streamlit 介面 ---
st.set_page_config(page_title="Google Maps 爬蟲", page_icon="📍")
st.title("📍 Google Maps 評論爬蟲工具")
st.info(f"當前目標：{SEARCH_QUERY}")

if st.button("🚀 開始爬取資料"):
    with st.spinner("瀏覽器啟動中，請稍候..."):
        driver = init_driver()
        try:
            results = scrape_google_reviews(driver, SEARCH_QUERY)
            
            if results:
                df = pd.DataFrame(results)
                st.success(f"✅ 完成！共抓取 {len(df)} 則評論。")
                st.dataframe(df)
                
                # 下載按鈕
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 下載評論 CSV",
                    data=csv,
                    file_name=f"{SEARCH_QUERY}_reviews.csv",
                    mime="text/csv"
                )
            else:
                st.error("❌ 沒抓到任何資料，請檢查店家名稱或增加滾動次數。")
        except Exception as e:
            st.error(f"發生程式錯誤: {e}")
        finally:
            driver.quit()
