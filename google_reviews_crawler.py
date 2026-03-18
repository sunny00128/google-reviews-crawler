import streamlit as st
import pandas as pd
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 瀏覽器初始化 ---
def init_driver():
    options = Options()
    options.add_argument("--headless=new") # 雲端執行必備
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=zh-TW")
    
    # 強制指向 Streamlit Cloud 的路徑
    if os.path.exists("/usr/bin/chromium"):
        options.binary_location = "/usr/bin/chromium"
        
    try:
        # 優先嘗試系統路徑
        service = Service("/usr/bin/chromedriver")
        return webdriver.Chrome(service=service, options=options)
    except:
        # 備用方案
        return webdriver.Chrome(options=options)

# --- 爬蟲邏輯 ---
def scrape_google_reviews(driver, shop_name, max_count=10):
    wait = WebDriverWait(driver, 15)
    # 使用 Google 搜尋進入點，最穩定
    driver.get(f"https://www.google.com/search?q={shop_name}+評論")
    time.sleep(3)

    try:
        # 尋找「Google 評論」按鈕
        triggers = [
            "//a[contains(@data-async-trigger, 'review')]",
            "//a[contains(text(), '則評論')]",
            "//span[contains(text(), 'Google 評論')]"
        ]
        
        btn_found = False
        for xpath in triggers:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                btn.click()
                btn_found = True
                break
            except: continue
            
        if not btn_found:
            return None, "找不到評論按鈕，請嘗試更精確的店名。"

        time.sleep(3)
        
        reviews_data = []
        last_height = 0
        
        # 建立進度條
        pbar = st.progress(0)
        
        # 評論視窗容器
        container_xpath = "//div[contains(@class, 'review-dialog-list') or @role='main']"

        for i in range(15): # 最多捲動 15 次
            # 抓取目前的評論
            items = driver.find_elements(By.XPATH, "//div[@data-review-id] | //div[contains(@class, 'gws-localreviews__google-review')]")
            
            for item in items[len(reviews_data):]:
                try:
                    # 展開全文
                    try:
                        more = item.find_element(By.XPATH, ".//a[contains(text(), '全文') or contains(text(), 'More')]")
                        driver.execute_script("arguments[0].click();", more)
                    except: pass
                    
                    name = item.find_element(By.XPATH, ".//div[contains(@class, 'TS76Pe') or contains(@class, 'd4r55')]").text
                    content = item.find_element(By.XPATH, ".//span[contains(@class, 'review-full-text') or contains(@class, 'wiI7pd')]").text
                    reviews_data.append({"姓名": name, "內容": content})
                    
                    if len(reviews_data) >= max_count: break
                except: continue
            
            if len(reviews_data) >= max_count: break
            
            # 執行捲動
            try:
                scroll_div = driver.find_element(By.XPATH, container_xpath)
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div)
            except:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            time.sleep(2)
            pbar.progress(min(len(reviews_data)/max_count, 1.0))
            if len(items) == last_height: break
            last_height = len(items)

        return pd.DataFrame(reviews_data[:max_count]), None

    except Exception as e:
        return None, str(e)

# --- Streamlit 介面 ---
st.set_page_config(page_title="Google 評論爬蟲", page_icon="📝")
st.title("📝 Google 評論全自動爬蟲")
st.caption("適應於 Streamlit Cloud 環境之 Selenium 爬蟲")

with st.sidebar:
    st.header("參數設定")
    shop_input = st.text_input("店家名稱", value="十二段東山店")
    count_input = st.slider("抓取數量", 5, 50, 10)
    st.divider()
    st.write("提示：若失敗請嘗試加入城市名，如「台中十二段東山店」。")

if st.button("🚀 開始爬取資料", use_container_width=True):
    with st.spinner("正在啟動瀏覽器並搜尋..."):
        driver = init_driver()
        df, error = scrape_google_reviews(driver, shop_input, count_input)
        driver.quit()
        
        if error:
            st.error(f"發生錯誤：{error}")
        elif df is not None and not df.empty:
            st.success(f"成功抓取 {len(df)} 則評論！")
            st.dataframe(df, use_container_width=True)
            
            # 下載功能
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載 CSV 結果", csv, f"{shop_input}.csv", "text/csv")
        else:
            st.warning("未抓取到任何資料，請確認店名是否正確。")
