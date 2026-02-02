import os
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import hashlib

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


SELECTORS = {
    "seatmap_ready": "#canvasWrapperdeparture-0",
    "wagon_buttons": ".wagonMap .btnWagon",
    "wagon_buttons_fallback": ".wagonMap button",
    "seat_saleable_css": "#canvasWrapperdeparture-0 .seatMapClick:not(.notSaleable)",
    "seat_number_inside": ".seatMapClick .seatNumber",
    "loading_any": ".vld-overlay.is-active",
    "sidebar": "#seatmapSelectedSeat",
    "sidebar_toggle": 'button[aria-controls="seatmapSelectedSeat"]',
    "gender_male": 'input[name="gender1"][value="MALE"]',
    "gender_female": 'input[name="gender1"][value="FEMALE"]',
    "sidebar_confirm": ".b-sidebar-footer button.btn-primary",
    "seat_click_saleable_css": "#canvasWrapperdeparture-0 .seatMapClick:not(.notSaleable)",
    "gender_popover_body": ".popover-body",
    "gender_popover_buttons": ".popover-body .popoverBtn",
    "gender_popover_women_img": ".popover-body img[alt*='women']",
    "gender_popover_man_img": ".popover-body img[alt*='man']",
}


def normalize_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return "https://example.com"
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "https://" + u
    return u


def make_driver(headless: bool) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,900")
    options.add_argument("--disable-gpu")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver


def wait_visible(driver: webdriver.Chrome, selector: str, timeout: int = 20):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
    )


def wait_gone(driver: webdriver.Chrome, selector: str, timeout: int = 20):
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
        )
    except TimeoutException:
        pass


def open_sidebar_if_needed(driver: webdriver.Chrome):
    sidebar = driver.find_element(By.CSS_SELECTOR, SELECTORS["sidebar"])
    if sidebar.value_of_css_property("display") == "none":
        driver.find_element(By.CSS_SELECTOR, SELECTORS["sidebar_toggle"]).click()
        wait_visible(driver, SELECTORS["sidebar"], timeout=10)
    wait_gone(driver, SELECTORS["loading_any"], timeout=10)


def click_gender(driver: webdriver.Chrome, gender: str):
    # Inputs can be non-interactable; click the label instead.
    if gender == "FEMALE":
        xpath = "//div[@id='seatmapSelectedSeat']//label[.//input[@name='gender1' and @value='FEMALE']]"
    else:
        xpath = "//div[@id='seatmapSelectedSeat']//label[.//input[@name='gender1' and @value='MALE']]"
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    ).click()


def click_gender_popover(driver: webdriver.Chrome, gender: str) -> bool:
    try:
        popover = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, SELECTORS["gender_popover_body"]))
        )
    except TimeoutException:
        return False
    try:
        if gender == "FEMALE":
            img = popover.find_element(By.CSS_SELECTOR, SELECTORS["gender_popover_women_img"])
        else:
            img = popover.find_element(By.CSS_SELECTOR, SELECTORS["gender_popover_man_img"])
        driver.execute_script("arguments[0].click();", img)
        return True
    except Exception:
        pass
    try:
        buttons = popover.find_elements(By.CSS_SELECTOR, SELECTORS["gender_popover_buttons"])
        if not buttons:
            return False
        if gender == "FEMALE":
            idx = 0
        else:
            idx = 1 if len(buttons) > 1 else 0
        driver.execute_script("arguments[0].click();", buttons[idx])
        return True
    except Exception:
        return False


def sidebar_has_selected_seat(driver: webdriver.Chrome) -> bool:
    return get_sidebar_seat_number(driver) is not None


def get_sidebar_seat_number(driver: webdriver.Chrome):
    try:
        seat_span = driver.find_element(
            By.XPATH,
            "//div[@id='seatmapSelectedSeat']//p[contains(.,'Koltuk')]/span[normalize-space()!='']",
        )
        if not seat_span.is_displayed():
            return None
        text = seat_span.text.strip()
        return text or None
    except Exception:
        return None


def confirm_button_enabled(driver: webdriver.Chrome) -> bool:
    try:
        btn = driver.find_element(By.CSS_SELECTOR, SELECTORS["sidebar_confirm"])
        if not btn.is_displayed():
            return False
        if btn.get_attribute("disabled") is not None:
            return False
        if "disabled" in (btn.get_attribute("class") or ""):
            return False
        return btn.is_enabled()
    except Exception:
        return False


def play_alert_sound():
    # Best-effort beep on macOS; fallback to terminal bell.
    try:
        subprocess.run(["osascript", "-e", "beep 1"], check=False, timeout=2)
    except Exception:
        pass
    try:
        print("\a", end="", flush=True)
    except Exception:
        pass


def speak_alert(message: str):
    try:
        subprocess.run(["say", message], check=False, timeout=5)
    except Exception:
        pass


def alert_for_duration(message: str, seconds: int, sound: bool):
    end_time = time.time() + max(0, seconds)
    if sound:
        speak_alert(message)
    while time.time() < end_time:
        print(message)
        if sound:
            play_alert_sound()
        time.sleep(2)


def choose_first_available_seat(driver: webdriver.Chrome, gender: str, confirm: bool):
    seats = driver.find_elements(By.CSS_SELECTOR, SELECTORS["seat_saleable_css"])
    if not seats:
        return False
    for seat in seats:
        try:
            if not seat.is_displayed():
                continue
            prev_seat = get_sidebar_seat_number(driver)
            driver.execute_script("arguments[0].click();", seat)
            wait_gone(driver, SELECTORS["loading_any"], timeout=10)
            # Some pages auto-open the sidebar on seat selection; only toggle if needed.
            try:
                sidebar = driver.find_element(By.CSS_SELECTOR, SELECTORS["sidebar"])
                if not sidebar.is_displayed():
                    open_sidebar_if_needed(driver)
            except Exception:
                open_sidebar_if_needed(driver)
            click_gender(driver, gender)
            if not WebDriverWait(driver, 5).until(lambda d: sidebar_has_selected_seat(d)):
                continue
            current_seat = get_sidebar_seat_number(driver)
            if current_seat is None or current_seat == prev_seat:
                continue
            if not confirm_button_enabled(driver):
                continue
            if confirm:
                driver.find_element(By.CSS_SELECTOR, SELECTORS["sidebar_confirm"]).click()
            return True
        except (StaleElementReferenceException, TimeoutException):
            continue
    return False


def scan_wagons_for_seat(driver: webdriver.Chrome, gender: str, confirm: bool) -> bool:
    wagon_buttons = driver.find_elements(By.CSS_SELECTOR, SELECTORS["wagon_buttons"])
    if not wagon_buttons:
        wagon_buttons = driver.find_elements(By.CSS_SELECTOR, SELECTORS["wagon_buttons_fallback"])
    wagon_buttons = [b for b in wagon_buttons if b.is_displayed()]
    candidates = []
    for b in wagon_buttons:
        if "disabled" in (b.get_attribute("class") or ""):
            continue
        if b.get_attribute("aria-disabled") == "true":
            continue
        candidates.append(b)
    if not candidates:
        return False
    for btn in candidates:
        try:
            if "active" not in btn.get_attribute("class"):
                driver.execute_script("arguments[0].click();", btn)
                wait_gone(driver, SELECTORS["loading_any"], timeout=10)
        except StaleElementReferenceException:
            continue
    return False


def current_wagon_label(btn) -> str:
    text = (btn.text or "").strip().split("\n")
    return text[0].strip() if text else "Vagon"


def find_available_seats_in_current_wagon(driver: webdriver.Chrome):
    seats = driver.find_elements(By.CSS_SELECTOR, SELECTORS["seat_click_saleable_css"])
    found = []
    empty_hashes_raw = os.getenv("EMPTY_IMG_HASHES", "").strip()
    empty_hashes = {h.strip().lower() for h in empty_hashes_raw.split(",") if h.strip()}
    for seat in seats:
        try:
            cls = (seat.get_attribute("class") or "")
            if "notSaleable" in cls:
                continue
            if seat.get_attribute("aria-disabled") == "true":
                continue
            img_src = ""
            try:
                img_src = seat.find_element(By.CSS_SELECTOR, "img").get_attribute("src") or ""
            except Exception:
                pass
            img_hash = hashlib.md5(img_src.encode("utf-8")).hexdigest() if img_src else ""
            if empty_hashes and img_hash not in empty_hashes:
                continue
            number_el = seat.find_element(By.CSS_SELECTOR, SELECTORS["seat_number_inside"])
            num = (number_el.text or "").strip()
            if num:
                found.append((num, seat))
        except Exception:
            continue
    return found


def select_seat_in_current_wagon(
    driver: webdriver.Chrome, seat_entries, gender: str, confirm: bool
):
    for num, seat in seat_entries:
        try:
            if not seat.is_displayed():
                continue
            driver.execute_script("arguments[0].click();", seat)
            wait_gone(driver, SELECTORS["loading_any"], timeout=10)
            if click_gender_popover(driver, gender):
                return num
            try:
                open_sidebar_if_needed(driver)
                click_gender(driver, gender)
                if confirm and confirm_button_enabled(driver):
                    driver.find_element(By.CSS_SELECTOR, SELECTORS["sidebar_confirm"]).click()
                return num
            except Exception:
                continue
        except (StaleElementReferenceException, TimeoutException):
            continue
    return None


def main():
    env_path = Path(__file__).with_name(".env")
    load_dotenv(dotenv_path=env_path)

    url = normalize_url(os.getenv("TARGET_URL"))
    headless = os.getenv("HEADLESS", "0") == "1"
    gender = os.getenv("GENDER", "MALE").upper()
    confirm = os.getenv("CONFIRM_SEAT", "0") == "1"
    auto_select = os.getenv("AUTO_SELECT", "0") == "1"
    poll_interval = float(os.getenv("POLL_INTERVAL", "2.0"))
    sound_enabled = os.getenv("SOUND", "0") == "1"
    sound_duration = int(float(os.getenv("SOUND_DURATION", "20")))

    print("ENV PATH:", env_path)
    print("URL:", url)
    print("GENDER:", gender, "| CONFIRM_SEAT:", confirm)

    driver = make_driver(headless)
    try:
        driver.get(url)
        wait_visible(driver, SELECTORS["seatmap_ready"], timeout=30)
        wait_gone(driver, SELECTORS["loading_any"], timeout=20)

        if auto_select:
            print("Seat map hazır. Vagonlar arasında geziliyor (otomatik seçim açık).")
        else:
            print("Seat map hazır. Vagonlar arasında geziliyor (koltuk seçimi devre dışı).")
        last_alert = set()
        while True:
            found = False
            wagon_buttons = driver.find_elements(By.CSS_SELECTOR, SELECTORS["wagon_buttons"])
            if not wagon_buttons:
                wagon_buttons = driver.find_elements(By.CSS_SELECTOR, SELECTORS["wagon_buttons_fallback"])
            wagon_buttons = [b for b in wagon_buttons if b.is_displayed()]
            for btn in wagon_buttons:
                if "disabled" in (btn.get_attribute("class") or ""):
                    continue
                if btn.get_attribute("aria-disabled") == "true":
                    continue
                if "active" not in btn.get_attribute("class"):
                    driver.execute_script("arguments[0].click();", btn)
                    wait_gone(driver, SELECTORS["loading_any"], timeout=10)
                seat_entries = find_available_seats_in_current_wagon(driver)
                if seat_entries:
                    label = current_wagon_label(btn)
                    seats = [n for n, _ in seat_entries]
                    keyed = [f"{label}:{s}" for s in seats]
                    new_seats = [s for s, k in zip(seats, keyed) if k not in last_alert]
                    if new_seats:
                        print(f"Koltuk boşaldı: {label} -> {', '.join(new_seats)}")
                        last_alert.update(keyed)
                        if auto_select:
                            selected = select_seat_in_current_wagon(
                                driver, seat_entries, gender, confirm
                            )
                            if selected:
                                print(f"Koltuk seçildi: {label} -> {selected}")
                        found = True
                        break
            if found:
                alert_for_duration(
                    "Koltuk bulundu da! Bu vagonda bekleniyor.",
                    sound_duration,
                    sound_enabled,
                )
                input("Devam etmek için Enter...")
            time.sleep(poll_interval)

        input("Kapatmak için Enter...")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
