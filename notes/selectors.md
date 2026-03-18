# TCDD DOM Snapshot
> Not: ID’ler (ör. `#__BVID__101`) dinamik olabildiği için **ID’ye bağlı uzun selector** kullanma.
> Öncelik sırası: **id > selenium-test > aria-label > class/structure**.

## 01 - Search Page
Snapshot: `docs/01_search_page.html`

### Zorunlu akış (input/dropdown açma)
- from_open: `#fromTrainInput`
- to_open: `#toTrainInput`  (from seçilmeden `readonly/disabled` olabilir)
- swap_button: `img.imgFromTo`

### Kalkış dropdown içi
- from_dropdown_container: `.whereFromDropdown`
- from_dropdown_menu: `.whereFromDropdown .dropdown-menu`
- from_search_input: `.whereFromDropdown input[aria-label="departureInput"]`

### Varış dropdown içi
- to_dropdown_container: `.toWhereDropdown`
- to_dropdown_menu: `.toWhereDropdown .dropdown-menu`
- to_search_input: `.toWhereDropdown input[aria-label="arrivalInput"]`

### Tarih
- date_open: `.seferSearchDateRangePicker input[placeholder="GidişTarihi"]`
  - alt: `input.calenderPurpleImg[placeholder="GidişTarihi"]`

### Yolcu
- passenger_open: `.passengerNumber input[placeholder="Yolcu Sayısı"]`
  - alt: `.passengerNumber input[selenium-test="passenger"]`
  - alt: `.passengerNumber input[aria-label="Yolcu Sayısı"]`

#### Yolcu panel içi
- passenger_minus: `.passengerNumber button[aria-label="btnRemove"]`
- passenger_plus: `.passengerNumber button[aria-label="btnAdd"]`
- passenger_quantity: `.passengerNumber input[aria-label="quantityNumber"]`
- passenger_apply: `.passengerNumber button[selenium-test="passenger-btn"]`

### Arama
- search_button: `#searchSeferButton`

### Ready / Wait
- page_ready_condition: `#searchSeferButton`
- loading_spinner_global (varsa): `.vld-overlay.is-active`  (display:none değilken)

---
## 02 - Trip List
Snapshot: docs/02_trip_list.html

### Sayfa hazır olma koşulu
- page_ready: `#seferListScroll`

### Yüklenme göstergesi (var)
- loading_spinner: `.vld-background, .vld-icon`

### Sefer listesi ana container
- trip_list_container: `#seferListScroll`

### Her bir sefer kartı
- trip_card: `.seferInformationArea .departureAccordion`

### Sefer başlığı / tren bilgisi
- trip_title: `.cardStation`
- trip_train_code: `h6 small`
- trip_duration: `p:not(.cardStation)`

### Saat bilgileri (kalkış - varış)
- trip_time_range: `time.text-danger`

### Sefer kartını genişletme (Daha fazla bilgi)
- trip_expand_button: `button.btnTicketType`

### Bilet tipi seçimleri
- ticket_type_buttons: `button[id*="ticketType"]`
- ticket_type_active: `button[id*="ticketType"].active`

### Vagon tipi seçimleri
- wagon_buttons: `button[id*="vagonType"]`
- wagon_active: `button[id*="vagonType"].active`
- wagon_disabled: `button[id*="vagonType"].disabled`

### Fiyat ve boş koltuk bilgisi
- wagon_price: `.priceArea .price`
- wagon_empty_seat: `.emptySeat`

### Koltuk seçimine geçiş
- go_seat_selection: `a[href="/koltuk-haritasi"]`

### Akış mantığı
```text
WAIT page_ready
WAIT spinner gone

FOR each trip_card:
    expand trip
    choose first non-disabled wagon
    read price + empty seats
    break

CLICK go_seat_selection
```


## 03 - Seat Map (Koltuk Haritası)
Snapshot: `docs/03_seat_map.html`

### Sayfa kimliği / ready
- page_ready_condition: `#canvasWrapperdeparture-0`

### Vagon seçimi (üstteki vagon butonları)
- wagon_bar_container: `.wagonMap`
- wagon_buttons: `.wagonMap .btnWagon`
- wagon_active: `.wagonMap .btnWagon.active`

### 🔹 VAGON TİPİ AYRIMI (KRİTİK)

> Business / Ekonomi ayrımı **koltuk renginden yapılmaz**.  
> Ayrım **vagon container** üzerinden yapılır.

#### Business Vagon (2+1)
- business_wagon_container: `[data-wagon-type="BUSINESS"], .wagon.business`
- business_seat_all: `[data-wagon-type="BUSINESS"] .seatMapClick`
- business_seat_saleable: `[data-wagon-type="BUSINESS"] .seatMapClick:not(.notSaleable)`
- business_seat_not_saleable: `[data-wagon-type="BUSINESS"] .seatMapClick.notSaleable`

#### Ekonomi Vagon (2+2)
- economy_wagon_container: `[data-wagon-type="ECONOMY"], .wagon.economy`
- economy_seat_all: `[data-wagon-type="ECONOMY"] .seatMapClick`
- economy_seat_saleable: `[data-wagon-type="ECONOMY"] .seatMapClick:not(.notSaleable)`
- economy_seat_not_saleable: `[data-wagon-type="ECONOMY"] .seatMapClick.notSaleable`

---

### Koltuk grid alanı
- seatmap_canvas: `.seatMapCanvas`
- canvas_wrapper: `#canvasWrapperdeparture-0`

### Koltuk elementleri
- seat_click_all: `#canvasWrapperdeparture-0 .seatMapClick`
- seat_click_saleable: `#canvasWrapperdeparture-0 .seatMapClick:not(.notSaleable)`
- seat_click_not_saleable: `#canvasWrapperdeparture-0 .seatMapClick.notSaleable`
- seat_number_inside: `.seatMapClick .seatNumber`
- seat_img_inside: `.seatMapClick img.carItemImg`

> Seçilebilir koltuğu “boş” diye ayırmanın en stabil yolu: `.notSaleable` olmayanı tıklamak.

### Vagonlar arası sağ/sol kaydırma (canvas okları)
- canvas_left_button: `.leftArea button.btnArrow`
- canvas_right_button: `.rightArea button.btnArrow`

### Geri
- back_button: `button.btnPrev`  (metni “Geri”)

### Seçimi bitir / tamamla
- complete_selection_button: `button[selenium-test="departure-0"]`  (metni “Seçimi Tamamla”, bazen display:none)

### Seçilen koltuk sidebar (sağ panel)
- selected_seat_sidebar_outer: `.seatMapSelectedSeat`
- selected_seat_sidebar: `#seatmapSelectedSeat`
- selected_seat_sidebar_toggle: `button[aria-controls="seatmapSelectedSeat"]`
- selected_seat_gender_male: `#seatmapSelectedSeat input[name="gender1"][value="MALE"]`
- selected_seat_gender_female: `#seatmapSelectedSeat input[name="gender1"][value="FEMALE"]`
- selected_seat_confirm_button: `.b-sidebar-footer button.btn-primary`  (metni “Seç”)

### Loading / overlay
- loading_spinner_seatmap: `#canvasWrapperdeparture-0 .vld-overlay.is-active.loadingSeatMap`  (display:none değilken)
- loading_spinner_global: `.vld-overlay.is-active`  (display:none değilken)
