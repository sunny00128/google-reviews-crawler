import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os

def init_driver():
    options = Options()
    # 這些參數是雲端執行的「保命符」
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # 強制指定 Chromium 瀏覽器的位置 (Streamlit Cloud 預設安裝路徑)
    options.binary_location = "/usr/bin/chromium"

    # 指定 Driver 路徑
    service = Service("/usr/bin/chromedriver")
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        st.error(f"驅動程式啟動失敗：{e}")
        # 如果失敗，嘗試不指定二進位路徑的備案
        return webdriver.Chrome(options=options)

# --- 主程式 ---
st.title("Google Reviews Crawler")

if st.button("啟動爬蟲"):
    with st.spinner("正在啟動瀏覽器..."):
        driver = init_driver()
        if driver:
            driver.get("https://www.google.com/maps")
            st.success(f"成功連線！網頁標題：{driver.title}")
            driver.quit()
