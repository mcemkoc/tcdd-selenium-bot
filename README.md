# TCDD DOM Snapshot & Selector Notes

Bu repository, TCDD bilet akışındaki sayfaların **DOM yapısını incelemek**,  
**stabil selector’ları çıkarmak** ve **otomasyon/QA çalışmaları için referans** oluşturmak amacıyla hazırlanmıştır.

> Amaç:  
> - Kırılgan `copy selector` / `nth-child` kullanımından kaçınmak  
> - SPA (Vue) tabanlı sayfalarda **state bağımlı DOM**’u doğru anlamak  
> - Selector + sayfa snapshot’larını tek yerde tutmak

---

## Hızlı Başlangıç

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
| --- | --- | --- |
| `TARGET_URL` | `https://example.com` | TCDD sayfa URL’si |
| `HEADLESS` | `0` | `1` ise headless çalışır |
| `GENDER` | `MALE` | `MALE` / `FEMALE` |
| `CONFIRM_SEAT` | `0` | `1` ise koltuğu onaylar |
| `AUTO_SELECT` | `0` | `1` ise bulduğu koltuğu seçer |
| `SOUND` | `1` | `1` ise sesli uyarı verir |
| `SOUND_DURATION` | `20` | saniye cinsinden uyarı süresi |
| `POLL_INTERVAL` | `2.0` | saniye cinsinden bekleme |
| `EMPTY_IMG_HASHES` | boş | virgüllü hash listesi |

## Proje Yapısı

```text
.
├── docs/
│   ├── 01_search_page.html      # Arama ekranı DOM snapshot
│   ├── 02_trip_list.html        # Sefer listesi DOM snapshot
│   ├── 03_seat_map.html         # Koltuk haritası DOM snapshot
│   ├── 04_seat_map_hover.html   # Hover + cinsiyet popup DOM snapshot
│   └── 05_seat_map_selected_screen.html # Seçim sonrası panel DOM snapshot
│
├── notes/
│   ├── selectors.md             # Tüm sayfalar için selector defteri
│   └── flow_warnings.md         # Akış/state/SPA uyarıları
│
└── README.md
```
