import streamlit as st
import pandas as pd
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 1. 初始化瀏覽器 (針對 Streamlit Cloud 優化) ---
def init_driver():
    options = Options()
    options.add_argument("--headless=new")  # 雲端必須開啟無頭模式
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=zh-TW")
    
    # Streamlit Cloud 的 Chromium 預設路徑
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        st.error(f"瀏覽器啟動失敗，嘗試備用方案... 錯誤: {e}")
        # 備用方案：交給 Selenium 自動尋找
        return webdriver.Chrome(options=options)

# --- 2. 爬蟲核心邏輯 ---
def scrape_google_reviews(driver, shop_name, max_reviews=20):
    wait = WebDriverWait(driver, 20)
    
    # 搜尋店家
    driver.get(f"https://www.google.com.tw/maps/search/{shop_name}")
    time.sleep(5)
    
    try:
        # 點擊評論分頁
        reviews_tab = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(@aria-label, '評論') or .//div[contains(text(),'評論')]]")
        ))
        reviews_tab.click()
        time.sleep(3)
        
        # 滾動加載評論
        scrollable_div = driver.find_element(By.XPATH, "//div[@role='main' or @role='feed' or contains(@class, 'm67q60')]")
        
        collected_data = []
        last_count = 0
        
        progress_bar = st.progress(0)
        
        while len(collected_data) < max_reviews:
            # 捲動到底部
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(2)
            
            # 抓取目前的評論元素
            items = driver.find_elements(By.XPATH, "//div[@data-review-id]")
            
            for item in items[last_count:]:
                try:
                    # 展開全文
                    try:
                        more_btn = item.find_element(By.XPATH, ".//button[contains(text(), '全文') or contains(text(), 'More')]")
                        driver.execute_script("arguments[0].click();", more_btn)
                    except: pass
                    
                    name = item.find_element(By.CLASS_NAME, "d4r55").text
                    rating = item.find_element(By.XPATH, ".//span[@role='img']").get_attribute("aria-label")
                    content = item.find_element(By.CLASS_NAME, "wiI7pd").text
                    
                    collected_data.append({"姓名": name, "星級": rating, "內容": content})
                    if len(collected_data) >= max_reviews: break
                except:
                    continue
            
            if len(items) == last_count: # 沒再增加了
                break
            last_count = len(items)
            progress_bar.progress(min(len(collected_data) / max_reviews, 1.0))

        return collected_data
    except Exception as e:
        st.error(f"爬取過程發生錯誤: {e}")
        return []

# --- 3. Streamlit 介面 ---
st.set_page_config(page_title="Google Maps 評論爬蟲", layout="wide")
st.title("📍 Google Maps 評論爬蟲工具")

col1, col2 = st.columns(2)
with col1:
    target_shop = st.text_input("輸入店家名稱：", placeholder="例如：十二段東山店")
with col2:
    num_reviews = st.number_input("預計抓取數量：", min_value=5, max_value=100, value=20)

if st.button("開始執行爬蟲"):
    if not target_shop:
        st.warning("請輸入店家名稱！")
    else:
        with st.spinner(f"正在分析 {target_shop} ..."):
            driver = init_driver()
            results = scrape_google_reviews(driver, target_shop, num_reviews)
            driver.quit()
            
            if results:
                df = pd.DataFrame(results)
                st.success(f"✅ 成功抓取 {len(df)} 則評論")
                st.dataframe(df, use_container_width=True)
                
                # 下載功能
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 下載資料為 CSV",
                    data=csv,
                    file_name=f"{target_shop}_reviews.csv",
                    mime="text/csv"
                )
            else:
                st.error("找不到評論或抓取失敗。")
