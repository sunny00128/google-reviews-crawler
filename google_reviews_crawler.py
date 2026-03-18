"""
Google Maps 評論爬蟲 - 十二段東山店
需要安裝：pip install selenium webdriver-manager pandas
"""

import time
import csv
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

SEARCH_QUERY = "十二段東山店"
OUTPUT_FILE = "十二段東山店_reviews.csv"
SCROLL_PAUSE = 2      # 每次滾動等待秒數
MAX_SCROLLS = 50      # 最多滾動次數（約可抓 10~20 則/次）


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--lang=zh-TW")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 若不想看到瀏覽器視窗，取消下一行註解
    # options.add_argument("--headless=new")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.maximize_window()
    return driver


def search_place(driver, query):
    driver.get("https://www.google.com/maps")
    wait = WebDriverWait(driver, 15)
    search_box = wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
    search_box.clear()
    search_box.send_keys(query)
    search_box.send_keys(Keys.ENTER)
    time.sleep(3)


def click_reviews_tab(driver):
    wait = WebDriverWait(driver, 15)
    try:
        # 點擊「評論」分頁
        reviews_tab = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(@aria-label, '評論') or contains(@aria-label, 'Reviews')]")
        ))
        reviews_tab.click()
        time.sleep(2)
        return True
    except TimeoutException:
        print("找不到評論分頁，請確認店家名稱是否正確。")
        return False


def scroll_reviews(driver):
    """滾動評論面板以載入更多評論"""
    try:
        # 找到評論可滾動的容器
        scrollable = driver.find_element(
            By.XPATH,
            "//div[@role='feed']"
        )
    except NoSuchElementException:
        print("找不到評論列表容器")
        return

    for i in range(MAX_SCROLLS):
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable)
        time.sleep(SCROLL_PAUSE)
        print(f"滾動第 {i + 1} 次...")

        # 檢查是否已載入全部（出現「已顯示全部評論」之類的文字）
        page_source = driver.page_source
        if "沒有更多評論" in page_source or "No more reviews" in page_source:
            print("已載入所有評論。")
            break

    # 展開所有「查看更多」
    expand_buttons = driver.find_elements(
        By.XPATH,
        "//button[contains(@aria-label, '查看更多') or contains(text(), '查看更多') or contains(text(), 'More')]"
    )
    for btn in expand_buttons:
        try:
            driver.execute_script("arguments[0].click();", btn)
        except Exception:
            pass
    time.sleep(1)


def parse_reviews(driver):
    reviews = []
    review_elements = driver.find_elements(
        By.XPATH,
        "//div[@data-review-id]"
    )

    print(f"共找到 {len(review_elements)} 則評論元素")

    for elem in review_elements:
        try:
            # 評論者名稱
            try:
                name = elem.find_element(By.CLASS_NAME, "d4r55").text.strip()
            except NoSuchElementException:
                name = ""

            # 星級評分
            try:
                rating_elem = elem.find_element(By.XPATH, ".//span[@role='img']")
                rating_text = rating_elem.get_attribute("aria-label") or ""
                rating_match = re.search(r"(\d+(\.\d+)?)", rating_text)
                rating = rating_match.group(1) if rating_match else ""
            except NoSuchElementException:
                rating = ""

            # 評論日期
            try:
                date = elem.find_element(By.CLASS_NAME, "rsqaWe").text.strip()
            except NoSuchElementException:
                date = ""

            # 評論內容
            try:
                content = elem.find_element(By.CLASS_NAME, "wiI7pd").text.strip()
            except NoSuchElementException:
                content = ""

            if name or content:
                reviews.append({
                    "姓名": name,
                    "星級": rating,
                    "日期": date,
                    "評論": content,
                })
        except Exception as e:
            print(f"解析評論時發生錯誤：{e}")
            continue

    return reviews


def save_to_csv(reviews, filename):
    if not reviews:
        print("沒有評論資料可儲存。")
        return
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["姓名", "星級", "日期", "評論"])
        writer.writeheader()
        writer.writerows(reviews)
    print(f"已儲存 {len(reviews)} 則評論至 {filename}")


def main():
    print(f"開始爬取「{SEARCH_QUERY}」的 Google 評論...")
    driver = init_driver()
    try:
        search_place(driver, SEARCH_QUERY)
        if not click_reviews_tab(driver):
            return
        scroll_reviews(driver)
        reviews = parse_reviews(driver)
        save_to_csv(reviews, OUTPUT_FILE)
    finally:
        driver.quit()
        print("瀏覽器已關閉。")


if __name__ == "__main__":
    main()
