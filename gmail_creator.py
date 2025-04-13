import time
import random
import requests
import json
import undetected_chromedriver.v2 as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import urllib.parse as urlparse

# ========== Cấu hình ==========
API_KEY_2CAPTCHA = "49a8930b62bd8f1510a1332f85b47eb4"
GMAIL_SIGNUP_URL = "https://accounts.google.com/signup"

# ========== Tạo thông tin ngẫu nhiên ==========
def generate_account():
    first = random.choice(["An", "Bao", "Nam", "Linh", "Minh", "Tuan"])
    last = random.choice(["Tran", "Nguyen", "Pham", "Le", "Hoang"])
    username = f"{first.lower()}{last.lower()}{random.randint(1000,9999)}"
    password = f"{username}@Abc123"
    return first, last, username, password

# ========== Đọc proxy chưa dùng ==========
def get_next_proxy():
    with open("proxies.txt") as f:
        proxies = [line.strip() for line in f if line.strip()]

    used = set()
    try:
        with open("used_proxies.txt") as f:
            used = set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        pass

    for proxy in proxies:
        if proxy not in used:
            return proxy
    return None

# ========== Lưu proxy đã dùng ==========
def mark_proxy_used(proxy):
    with open("used_proxies.txt", "a") as f:
        f.write(proxy + "\n")

# ========== Giải reCAPTCHA với 2Captcha ==========
def solve_recaptcha(site_key, url):
    print("[~] Gửi yêu cầu giải CAPTCHA...")
    req = requests.post("http://2captcha.com/in.php", data={
        "key": API_KEY_2CAPTCHA,
        "method": "userrecaptcha",
        "googlekey": site_key,
        "pageurl": url,
        "json": 1
    })
    req_id = req.json().get("request")

    # Đợi kết quả
    for _ in range(30):
        time.sleep(5)
        res = requests.get("http://2captcha.com/res.php", params={
            "key": API_KEY_2CAPTCHA,
            "action": "get",
            "id": req_id,
            "json": 1
        })
        if res.json().get("status") == 1:
            print("[+] CAPTCHA giải thành công!")
            return res.json().get("request")
    print("[x] Giải CAPTCHA thất bại.")
    return None

# ========== Khởi tạo trình duyệt ==========
def create_browser(proxy=None):
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument(f"user-agent={UserAgent().random}")
    if proxy:
        options.add_argument(f'--proxy-server=http://{proxy}')
    return uc.Chrome(options=options)

# ========== Lưu tài khoản ==========
def save_account(email, password):
    with open("created_accounts.txt", "a") as f:
        f.write(f"{email}:{password}\n")

# ========== Hàm tạo Gmail ==========
def create_gmail(proxy):
    first, last, username, password = generate_account()
    email = f"{username}@gmail.com"

    print(f"[+] Đang tạo: {email} qua proxy {proxy}")
    driver = create_browser(proxy)
    wait = WebDriverWait(driver, 30)

    try:
        driver.get(GMAIL_SIGNUP_URL)
        wait.until(EC.presence_of_element_located((By.ID, "firstName")))

        driver.find_element(By.ID, "firstName").send_keys(first)
        driver.find_element(By.ID, "lastName").send_keys(last)
        driver.find_element(By.ID, "username").send_keys(username)
        driver.find_element(By.NAME, "Passwd").send_keys(password)
        driver.find_element(By.NAME, "ConfirmPasswd").send_keys(password)
        driver.find_element(By.XPATH, "//span[text()='Next']").click()

        # CAPTCHA xuất hiện → xử lý
        time.sleep(5)
        if "recaptcha" in driver.page_source.lower():
            soup = BeautifulSoup(driver.page_source, "html.parser")
            iframe = soup.find("iframe", src=lambda x: x and "recaptcha" in x)
            if iframe:
                src_url = iframe["src"]
                parsed = urlparse.urlparse(src_url)
                site_key = urlparse.parse_qs(parsed.query)["k"][0]
                print("[+] Sitekey tự động lấy:", site_key)
                token = solve_recaptcha(site_key, driver.current_url)
                if token:
                    driver.execute_script(
                        "document.getElementById('g-recaptcha-response').innerHTML = arguments[0]",
                        token
                    )
                    driver.execute_script("___grecaptcha_cfg.clients[0].R.R.callback(arguments[0])", token)
                    time.sleep(5)

        # Chờ tới bước tiếp theo hoặc xác minh số điện thoại
        time.sleep(10)
        print(f"[+] Thành công (có thể cần xác minh thủ công tiếp theo): {email}")
        save_account(email, password)

    except Exception as e:
        print(f"[x] Lỗi tạo tài khoản: {e}")
    finally:
        driver.quit()
        mark_proxy_used(proxy)

# ========== Vòng lặp chính ==========
if __name__ == "__main__":
    while True:
        proxy = get_next_proxy()
        if not proxy:
            print("[!] Hết proxy!")
            break
        create_gmail(proxy)
        print("[~] Đợi 15 giây trước lần tiếp theo...")
        time.sleep(15)
