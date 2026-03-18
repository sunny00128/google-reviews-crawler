import time
import csv
import re
import os
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定區 ---
SEARCH_QUERY = "十二段東山店"
OUTPUT_FILE = "reviews.csv"
SCROLL_PAUSE = 2
MAX_SCROLLS = 10  # 測試時建議先設小一點

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")  # 雲端執行必須開啟 headless
    
    # 檢查是否在 Streamlit Cloud 環境 (Linux)
    if os.path.exists("/usr/bin/chromium-browser"):
        options.binary_location = "/usr/bin/chromium-browser"
        service = Service("/usr/bin/chromedriver")
    else:
        # 本地開發環境 (請確保已安裝 webdriver-manager 或手動放置 chromedriver)
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        except ImportError:
            # 如果本地沒裝 webdriver-manager，請手動指定路徑
            service = Service()

    driver = webdriver.Chrome(service=service, options=options)
    return driver

def search_place(driver, query):
    driver.get("https://www.google.com/maps?hl=zh-TW")
    wait = WebDriverWait(driver, 20)
    search_box = wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
    search_box.clear()
    search_box.send_keys(query)
    search_box.send_keys(Keys.ENTER)
    time.sleep(5)

def click_reviews_tab(driver):
    wait = WebDriverWait(driver, 15)
    try:
        # 使用更強健的 XPATH 匹配
        reviews_tab = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(@aria-label, '評論') or .//div[text()='評論']]")
        ))
        reviews_tab.click()
        time.sleep(3)
        return True
    except:
        st.error("找不到評論分頁，可能是店家名稱不夠精確或 Google 版面跳轉。")
        return False

def scroll_reviews(driver):
    try:
        # Google Maps 評論滾動容器的特徵
        scrollable = driver.find_element(By.XPATH, "//div[@role='main' or @role='feed' or contains(@class, 'm67q60')]")
    except:
        st.warning("找不到滾動容器，將嘗試抓取目前畫面。")
        return

    for i in range(MAX_SCROLLS):
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable)
        time.sleep(SCROLL_PAUSE)
        if i % 5 == 0:
            st.write(f"正在載入更多評論... (第 {i+1} 次滾動)")

def parse_reviews(driver):
    reviews = []
    # 根據 2024/2025 Google Maps 結構更新的 Class Name
    review_elements = driver.find_elements(By.XPATH, "//div[@data-review-id]")
    
    st.info(f"偵測到 {len(review_elements)} 則初步內容，開始解析...")

    for elem in review_elements:
        try:
            # 展開「全文」
            try:
                more_btn = elem.find_element(By.XPATH, ".//button[contains(text(), '全文') or contains(text(), 'More')]")
                driver.execute_script("arguments[0].click();", more_btn)
            except:
                pass

            name = elem.find_element(By.CLASS_NAME, "d4r55").text.strip()
            rating_text = elem.find_element(By.XPATH, ".//span[@role='img']").get_attribute("aria-label")
            rating = re.search(r"\d", rating_text).group() if rating_text else ""
            date = elem.find_element(By.CLASS_NAME, "rsqaWe").text.strip()
            content = elem.find_element(By.CLASS_NAME, "wiI7pd").text.strip()

            reviews.append({
                "姓名": name,
                "星級": rating,
                "日期": date,
                "評論": content,
            })
        except:
            continue
    return reviews

def main():
    st.title("Google Maps 評論爬蟲工具")
    
    if st.button("開始爬取"):
        with st.spinner("啟動瀏覽器中..."):
            driver = init_driver()
            try:
                search_place(driver, SEARCH_QUERY)
                if click_reviews_tab(driver):
                    scroll_reviews(driver)
                    data = parse_reviews(driver)
                    
                    if data:
                        st.success(f"成功抓取 {len(data)} 則評論！")
                        st.table(data[:5]) # 預覽前五筆
                        
                        # 提供 CSV 下載
                        csv_data = "姓名,星級,日期,評論\n"
                        for row in data:
                            csv_data += f'"{row["姓名"]}","{row["星級"]}","{row["日期"]}","{row["評論"]}"\n'
                        
                        st.download_button(
                            label="點我下載 CSV 檔案",
                            data=csv_data.encode('utf-8-sig'),
                            file_name=OUTPUT_FILE,
                            mime='text/csv'
                        )
            except Exception as e:
                st.error(f"發生錯誤: {e}")
            finally:
                driver.quit()

if __name__ == "__main__":
    main()
