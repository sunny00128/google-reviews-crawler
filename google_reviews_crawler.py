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
    options.add_argument("--window-size=1920,1080") # 視窗大一點才不會漏掉按鈕
    
    # Streamlit Cloud 預設路徑
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    
    return webdriver.Chrome(service=service, options=options)

def scrape_reviews(driver, shop_name, max_count):
    wait = WebDriverWait(driver, 15)
    
    # 步驟 1: 使用 Google 搜尋，通常會直接跳出店家的知識面板
    search_url = f"https://www.google.com/search?q={shop_name}+評論"
    driver.get(search_url)
    time.sleep(3)

    try:
        # 步驟 2: 嘗試點擊「Google 評論」按鈕 (多重路徑嘗試)
        triggers = [
            "//a[contains(@data-async-trigger, 'review')]",
            "//a[contains(text(), '則評論')]",
            "//span[contains(text(), 'Google 評論')]",
            "//a[contains(@aria-label, '評論')]"
        ]
        
        clicked = False
        for xpath in triggers:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                btn.click()
                clicked = True
                break
            except: continue
            
        if not clicked:
            st.error("找不到評論按鈕，請嘗試輸入更精確的店名（例如：台中十二段東山店）")
            return []

        time.sleep(3) # 等待彈出視窗

        # 步驟 3: 捲動並爬取
        reviews_data = []
        last_len = 0
        
        # 評論視窗通常在這個 div 裡
        scrollable_xpath = "//div[contains(@class, 'review-dialog-list') or @role='main']"
        
        with st.status(f"正在分析 {shop_name}...", expanded=True) as status:
            for _ in range(20): # 最多捲動 20 次
                # 抓取目前的評論清單
                elements = driver.find_elements(By.XPATH, "//div[@data-review-id] | //div[contains(@class, 'gws-localreviews__google-review')]")
                
                for el in elements[last_len:]:
                    try:
                        # 姓名
                        name = el.find_element(By.XPATH, ".//div[contains(@class, 'TS76Pe') or contains(@class, 'd4r55')]").text
                        # 內容 (有些評論沒寫字，給空值)
                        try:
                            content = el.find_element(By.XPATH, ".//span[contains(@class, 'review-full-text') or contains(@class, 'wiI7pd')]").text
                        except:
                            content = "(無文字評論)"
                        
                        reviews_data.append({"姓名": name, "內容": content})
                    except: continue
                
                if len(reviews_data) >= max_count: break
                
                # 捲動
                try:
                    scroll_div = driver.find_element(By.XPATH, scrollable_xpath)
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div)
                except:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                time.sleep(2)
                status.write(f"已收集 {len(reviews_data)} 則評論...")
                
                if len(elements) == last_len: break # 沒新內容了
                last_len = len(elements)

        return reviews_data[:max_count]

    except Exception as e:
        st.error(f"執行中斷：{e}")
        return []

# ---介面---
st.title("🌟 Google 評論自動爬蟲")
shop = st.text_input("你想爬哪間店？", value="十二段東山店")
num = st.slider("抓取數量", 5, 50, 10)

if st.button("開始執行"):
    driver = init_driver()
    data = scrape_reviews(driver, shop, num)
    driver.quit()
    
    if data:
        df = pd.DataFrame(data)
        st.success("爬取完成！")
        st.table(df)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載 CSV", csv, f"{shop}.csv", "text/csv")
