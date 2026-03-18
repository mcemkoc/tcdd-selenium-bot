import os
import time
import subprocess
import hashlib
import traceback
import shutil
from pathlib import Path
from dotenv import load_dotenv

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    "seat_click_all_css": "#canvasWrapperdeparture-0 .seatMapClick",
    "gender_popover_body": ".popover-body",
    "gender_popover_buttons": ".popover-body .popoverBtn",
    "gender_popover_women_img": ".popover-body img[alt*='women']",
    "gender_popover_man_img": ".popover-body img[alt*='man']",
    "selected_seat_number": ".selectedSeatArea .textSeat strong",
}

ALERT_MESSAGE = "Koltuk buldum"


def parse_hash_list(raw: str):
    parsed = set()
    for part in (raw or "").split(","):
        h = part.strip().lower()
        if not h:
            continue
        if len(h) == 32 and all(c in "0123456789abcdef" for c in h):
            parsed.add(h)
    return parsed


def seat_img_hash(seat) -> str:
    try:
        img = seat.find_element(By.CSS_SELECTOR, "img")
        src = img.get_attribute("src") or ""
        return hashlib.md5(src.encode("utf-8")).hexdigest() if src else ""
    except Exception:
        return ""


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


def get_selected_seat_from_list(driver: webdriver.Chrome):
    try:
        el = driver.find_element(By.CSS_SELECTOR, SELECTORS["selected_seat_number"])
        if not el.is_displayed():
            return None
        text = (el.text or "").strip()
        return text or None
    except Exception:
        return None


def wait_selected_seat_change(driver: webdriver.Chrome, prev: str, timeout: int = 6):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: (get_selected_seat_from_list(d) or "") not in {"", prev or ""}
        )
        return get_selected_seat_from_list(driver)
    except TimeoutException:
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
    # Louder/more distinct macOS alert; fallback to beep + terminal bell.
    if shutil.which("afplay"):
        for sound_file in [
            "/System/Library/Sounds/Sosumi.aiff",
            "/System/Library/Sounds/Funk.aiff",
            "/System/Library/Sounds/Ping.aiff",
        ]:
            if os.path.exists(sound_file):
                try:
                    subprocess.run(["afplay", sound_file], check=False, timeout=2)
                    return
                except Exception:
                    pass
    try:
        subprocess.run(["osascript", "-e", "beep 2"], check=False, timeout=2)
    except Exception:
        pass
    try:
        print("\a\a", end="", flush=True)
    except Exception:
        pass


def speak_alert(message: str):
    try:
        subprocess.Popen(["say", message])
    except Exception:
        pass


def alert_for_duration(
    message: str, seconds: int, beep_enabled: bool, voice_enabled: bool
):
    end_time = time.time() + max(0, seconds)
    next_voice_at = 0.0
    while time.time() < end_time:
        now = time.time()
        print(message)
        if voice_enabled and now >= next_voice_at:
            speak_alert(message)
            next_voice_at = now + 4.0
        if beep_enabled:
            play_alert_sound()
        time.sleep(1)


def ensure_stop_button(driver: webdriver.Chrome):
    js = """
    if (!window.__BOT_STOP__) { window.__BOT_STOP__ = false; }
    if (!document.getElementById('bot-stop-btn')) {
      const btn = document.createElement('button');
      btn.id = 'bot-stop-btn';
      btn.textContent = 'Durdur';
      btn.style.position = 'fixed';
      btn.style.bottom = '16px';
      btn.style.right = '16px';
      btn.style.zIndex = '99999';
      btn.style.padding = '10px 14px';
      btn.style.borderRadius = '8px';
      btn.style.border = 'none';
      btn.style.background = '#d32f2f';
      btn.style.color = '#fff';
      btn.style.fontSize = '14px';
      btn.style.cursor = 'pointer';
      btn.onclick = () => { window.__BOT_STOP__ = true; };
      document.body.appendChild(btn);
    }
    """
    try:
        driver.execute_script(js)
    except Exception:
        pass


def stop_requested(driver: webdriver.Chrome) -> bool:
    try:
        return bool(driver.execute_script("return window.__BOT_STOP__ === true;"))
    except Exception:
        return False


def get_wagon_buttons(driver: webdriver.Chrome):
    wagon_buttons = driver.find_elements(By.CSS_SELECTOR, SELECTORS["wagon_buttons"])
    if not wagon_buttons:
        wagon_buttons = driver.find_elements(By.CSS_SELECTOR, SELECTORS["wagon_buttons_fallback"])
    return [b for b in wagon_buttons if b.is_displayed()]


def active_wagon_label(driver: webdriver.Chrome) -> str:
    for b in get_wagon_buttons(driver):
        try:
            if "active" in (b.get_attribute("class") or ""):
                return current_wagon_label(b)
        except StaleElementReferenceException:
            continue
    return ""


def activate_wagon(driver: webdriver.Chrome, btn, timeout: int = 8) -> bool:
    target_label = current_wagon_label(btn)
    try:
        if "active" in (btn.get_attribute("class") or ""):
            return True
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center', inline:'center'});", btn
        )
        driver.execute_script("arguments[0].click();", btn)
        wait_gone(driver, SELECTORS["loading_any"], timeout=10)
        WebDriverWait(driver, timeout).until(
            lambda d: active_wagon_label(d).lower() == target_label.lower()
        )
        return True
    except Exception:
        return False


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


def is_disabled_access_seat(seat, num: str) -> bool:
    # Engelli koltuklarını normal aramadan hariç tut.
    normalized_num = (num or "").strip().lower()
    if normalized_num.endswith("h"):
        return True
    try:
        alt = (seat.find_element(By.CSS_SELECTOR, "img").get_attribute("alt") or "")
        alt_upper = alt.upper().replace("İ", "I")
        if "ENGELLI KOLTUK" in alt_upper:
            return True
    except Exception:
        pass
    return False


def dump_seat_hashes(driver: webdriver.Chrome, only_seat: str = ""):
    target = (only_seat or "").strip().lower()
    print("DEBUG HASH DUMP START")
    seats = driver.find_elements(By.CSS_SELECTOR, SELECTORS["seat_click_all_css"])
    found_any = False
    for seat in seats:
        try:
            num_el = seat.find_element(By.CSS_SELECTOR, SELECTORS["seat_number_inside"])
            num = (num_el.text or "").strip().lower()
            if not num:
                continue
            if target and num != target:
                continue
            cls = (seat.get_attribute("class") or "").strip()
            aria = (seat.get_attribute("aria-disabled") or "").strip()
            img = seat.find_element(By.CSS_SELECTOR, "img")
            src = img.get_attribute("src") or ""
            alt = (img.get_attribute("alt") or "").strip()
            img_hash = seat_img_hash(seat)
            print(
                f"SEAT {num}: class={cls} aria={aria} alt={alt} img_hash={img_hash}"
            )
            found_any = True
        except Exception:
            continue
    if target and not found_any:
        print(f"SEAT {target}: bulunamadı")
    print("DEBUG HASH DUMP END")


def dump_hash_summary(driver: webdriver.Chrome):
    seats = driver.find_elements(By.CSS_SELECTOR, SELECTORS["seat_click_all_css"])
    summary = {}
    for seat in seats:
        try:
            num_el = seat.find_element(By.CSS_SELECTOR, SELECTORS["seat_number_inside"])
            num = (num_el.text or "").strip()
            if not num:
                continue
            h = seat_img_hash(seat)
            if not h:
                continue
            cls = (seat.get_attribute("class") or "").strip()
            state = "notSaleable" if "notSaleable" in cls else "saleable"
            data = summary.setdefault(h, {"count": 0, "saleable": 0, "samples": []})
            data["count"] += 1
            if state == "saleable":
                data["saleable"] += 1
            if len(data["samples"]) < 8:
                data["samples"].append(f"{num}({state})")
        except Exception:
            continue
    print("HASH SUMMARY START")
    for h, data in sorted(summary.items(), key=lambda item: item[1]["saleable"], reverse=True):
        samples = ", ".join(data["samples"])
        print(
            f"HASH {h} -> total={data['count']} saleable={data['saleable']} sample=[{samples}]"
        )
    print("HASH SUMMARY END")


def find_available_seats_in_current_wagon(driver: webdriver.Chrome, empty_hashes=None):
    seats = driver.find_elements(By.CSS_SELECTOR, SELECTORS["seat_click_all_css"])
    allowed_hashes = empty_hashes or set()
    found = []
    for seat in seats:
        try:
            if not seat.is_displayed():
                continue
            if seat.get_attribute("aria-disabled") == "true":
                continue
            number_el = seat.find_element(By.CSS_SELECTOR, SELECTORS["seat_number_inside"])
            num = (number_el.text or "").strip()
            if not num:
                continue
            if is_disabled_access_seat(seat, num):
                continue
            h = seat_img_hash(seat)
            if h not in allowed_hashes:
                continue
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
            prev_selected = get_selected_seat_from_list(driver)
            driver.execute_script("arguments[0].click();", seat)
            wait_gone(driver, SELECTORS["loading_any"], timeout=10)
            if not click_gender_popover(driver, gender):
                continue
            selected = wait_selected_seat_change(driver, prev_selected)
            if not selected:
                continue
            if selected.lower() != num.lower():
                continue
            return selected
        except (StaleElementReferenceException, TimeoutException):
            continue
        except Exception:
            print(f"Koltuk seçiminde hata ({num}):")
            traceback.print_exc()
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
    legacy_sound_enabled = os.getenv("SOUND", "0") == "1"
    beep_enabled = os.getenv("ALERT_BEEP", "1" if legacy_sound_enabled else "0") == "1"
    voice_enabled = os.getenv("ALERT_VOICE", "1" if legacy_sound_enabled else "0") == "1"
    sound_duration = int(float(os.getenv("SOUND_DURATION", "20")))
    debug_wagons = os.getenv("DEBUG_WAGONS", "0") == "1"
    dump_hashes_on_start = os.getenv("DUMP_HASHES_ON_START", "0") == "1"
    dump_hash_seat = os.getenv("DUMP_HASH_SEAT", "").strip()
    empty_img_hashes = parse_hash_list(os.getenv("EMPTY_IMG_HASHES", ""))
    trace_wagons = os.getenv("TRACE_WAGONS", "1") == "1"

    print("ENV PATH:", env_path)
    print("URL:", url)
    print("GENDER:", gender, "| CONFIRM_SEAT:", confirm)
    print("ALERT_BEEP:", beep_enabled, "| ALERT_VOICE:", voice_enabled)
    if empty_img_hashes:
        print("EMPTY_IMG_HASHES aktif:", ", ".join(sorted(empty_img_hashes)))
    else:
        print("EMPTY_IMG_HASHES boş: hash eşleşmesi olmadan koltuk seçimi yapılmayacak.")


    driver = make_driver(headless)
    try:
        driver.get(url)
        wait_visible(driver, SELECTORS["seatmap_ready"], timeout=30)
        wait_gone(driver, SELECTORS["loading_any"], timeout=20)
        ensure_stop_button(driver)
        if dump_hashes_on_start:
            dump_hash_summary(driver)
            dump_seat_hashes(driver, dump_hash_seat)
            input("Hash dump tamam. Devam etmek için Enter...")

        if auto_select:
            print("Seat map hazır. Vagonlar arasında geziliyor (otomatik seçim açık).")
        else:
            print("Seat map hazır. Vagonlar arasında geziliyor (koltuk seçimi devre dışı).")
        last_alert = set()
        while True:
            try:
                if stop_requested(driver):
                    print("Durdur butonu ile çıkış istendi.")
                    break
                # Önce aktif (mevcut) vagonu kontrol et.
                active_btn = None
                wagon_buttons = get_wagon_buttons(driver)
                for b in wagon_buttons:
                    if "active" in (b.get_attribute("class") or ""):
                        active_btn = b
                        break
                if active_btn:
                    active_label = current_wagon_label(active_btn)
                    if trace_wagons:
                        print(f"Vagon kontrol (aktif): {active_label}")
                    seat_entries = find_available_seats_in_current_wagon(driver, empty_img_hashes)
                    if trace_wagons:
                        print(f"  -> Uygun koltuk adedi: {len(seat_entries)}")
                    if seat_entries:
                        label = current_wagon_label(active_btn)
                        seats = [n for n, _ in seat_entries]
                        keyed = [f"{label}:{s}" for s in seats]
                        new_seats = [s for s, k in zip(seats, keyed) if k not in last_alert]
                        if new_seats:
                            if auto_select:
                                selected = select_seat_in_current_wagon(
                                    driver, seat_entries, gender, confirm
                                )
                                if selected:
                                    print(f"Koltuk seçildi: {label} -> {selected}")
                                    last_alert.update(keyed)
                                    alert_for_duration(
                                        ALERT_MESSAGE, sound_duration, beep_enabled, voice_enabled
                                    )
                                    cmd = input("Devam etmek için Enter, çıkmak için 'exit': ").strip().lower()
                                    if cmd == "exit":
                                        break
                                    time.sleep(poll_interval)
                                    continue
                                print("Koltuk bulundu ama seçim başarısız, tarama devam ediyor.")
                            else:
                                print(f"Koltuk boşaldı: {label} -> {', '.join(new_seats)}")
                                last_alert.update(keyed)
                                alert_for_duration(
                                    ALERT_MESSAGE, sound_duration, beep_enabled, voice_enabled
                                )
                                cmd = input("Devam etmek için Enter, çıkmak için 'exit': ").strip().lower()
                                if cmd == "exit":
                                    break
                                time.sleep(poll_interval)
                                continue
                found = False
                if debug_wagons:
                    print("DEBUG_WAGONS: data-original-title list:")
                    for b in wagon_buttons:
                        title = b.get_attribute("data-original-title") or ""
                        print("  -", title)
                for btn in wagon_buttons:
                    if "disabled" in (btn.get_attribute("class") or ""):
                        continue
                    if btn.get_attribute("aria-disabled") == "true":
                        continue
                    label = current_wagon_label(btn)
                    moved = activate_wagon(driver, btn)
                    if trace_wagons:
                        print(f"Vagon kontrol: {label} | geçiş={'OK' if moved else 'FAIL'}")
                    if not moved:
                        continue
                    seat_entries = find_available_seats_in_current_wagon(driver, empty_img_hashes)
                    if trace_wagons:
                        print(f"  -> Uygun koltuk adedi: {len(seat_entries)}")
                    if seat_entries:
                        seats = [n for n, _ in seat_entries]
                        keyed = [f"{label}:{s}" for s in seats]
                        new_seats = [s for s, k in zip(seats, keyed) if k not in last_alert]
                        if new_seats:
                            if auto_select:
                                selected = select_seat_in_current_wagon(
                                    driver, seat_entries, gender, confirm
                                )
                                if selected:
                                    print(f"Koltuk seçildi: {label} -> {selected}")
                                    last_alert.update(keyed)
                                    found = True
                                    break
                                print("Koltuk bulundu ama seçim başarısız, tarama devam ediyor.")
                                continue
                            else:
                                print(f"Koltuk boşaldı: {label} -> {', '.join(new_seats)}")
                                last_alert.update(keyed)
                                found = True
                                break
                if found:
                    alert_for_duration(
                        ALERT_MESSAGE, sound_duration, beep_enabled, voice_enabled
                    )
                    cmd = input("Devam etmek için Enter, çıkmak için 'exit': ").strip().lower()
                    if cmd == "exit":
                        break
            except Exception:
                print("Ana tarama döngüsünde beklenmeyen hata:")
                traceback.print_exc()
            time.sleep(poll_interval)

        input("Kapatmak için Enter...")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
