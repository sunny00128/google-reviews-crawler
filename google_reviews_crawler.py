import streamlit as st
import pandas as pd
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=zh-TW")
    # 模擬真人視窗大小，避免元素重疊
    options.add_argument("--window-size=1920,1080")
    
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    
    return webdriver.Chrome(service=service, options=options)

def scrape_google_reviews(driver, shop_name, max_reviews=20):
    wait = WebDriverWait(driver, 15)
    # 直接使用 Google 搜尋結果頁面，這通常比 Maps 直接搜更穩定
    search_url = f"https://www.google.com/search?q={shop_name}+Google+評論"
    driver.get(search_url)
    time.sleep(3)

    try:
        # 核心優化：嘗試多種方式找到「評論」按鈕
        # 1. 嘗試尋找搜尋結果中的 "評論" 連結
        review_triggers = [
            "//a[contains(@data-async-trigger, 'review')]",
            "//a[contains(@aria-label, '評論')]",
            "//span[contains(text(), '則評論')]",
            "//a[contains(text(), 'Google 評論')]"
        ]
        
        found_btn = False
        for xpath in review_triggers:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                btn.click()
                found_btn = True
                break
            except:
                continue
        
        if not found_btn:
            # 如果搜尋頁面找不到，嘗試切換到 Maps 模式
            driver.get(f"https://www.google.com.tw/maps/search/{shop_name}")
            time.sleep(5)
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, '評論')]")))
            btn.click()

        time.sleep(3)
        
        # 捲動與抓取邏輯
        collected_data = []
        last_height = 0
        
        # 尋找評論滾動容器 (Google 評論視窗的常見 Class)
        scrollable_div_xpath = "//div[contains(@class, 'review-dialog-list') or @role='main' or @role='feed']"
        
        with st.status(f"正在爬取 {shop_name}...", expanded=True) as status:
            while len(collected_data) < max_reviews:
                # 取得目前所有評論
                items = driver.find_elements(By.XPATH, "//div[@data-review-id] | //div[contains(@class, 'gws-localreviews__google-review')]")
                
                for item in items[len(collected_data):]:
                    try:
                        # 嘗試抓取姓名與內容
                        name = item.find_element(By.XPATH, ".//div[contains(@class, 'TS76Pe') or contains(@class, 'd4r55')]").text
                        content = item.find_element(By.XPATH, ".//span[contains(@class, 'review-full-text') or contains(@class, 'wiI7pd')]").text
                        
                        collected_data.append({"姓名": name, "內容": content})
                        if len(collected_data) >= max_reviews: break
                    except:
                        continue
                
                if len(collected_data) >= max_reviews: break
                
                # 捲動
                try:
                    scroll_target = driver.find_element(By.XPATH, scrollable_div_xpath)
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_target)
                except:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                time.sleep(2)
                status.write(f"已抓取: {len(collected_data)} 則...")
                
                # 防死循環：如果數量沒增加就跳出
                if len(items) == last_height: break
                last_height = len(items)

            status.update(label="爬取完成！", state="complete", expanded=False)
        return collected_data

    except Exception as e:
        st.error(f"詳細錯誤訊息: {str(e)[:200]}...") # 顯示前200字錯誤
        return []

# --- UI 介面 ---
st.title("🚀 Google 評論精準爬蟲")
shop = st.text_input("店家名稱", value="十二段東山店")
limit = st.slider("抓取數量", 5, 50, 10)

if st.button("開始執行"):
    driver = init_driver()
    results = scrape_google_reviews(driver, shop, limit)
    driver.quit()
    
    if results:
        df = pd.DataFrame(results)
        st.table(df)
        st.download_button("下載 CSV", df.to_csv(index=False).encode('utf-8-sig'), "data.csv")
    else:
        st.warning("未能成功獲取資料，請嘗試更精確的店名。")
