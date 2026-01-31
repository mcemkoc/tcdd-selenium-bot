# TCDD DOM Snapshot & Selector Notes

Bu repository, TCDD bilet akışındaki sayfaların **DOM yapısını incelemek**,  
**stabil selector’ları çıkarmak** ve **otomasyon/QA çalışmaları için referans** oluşturmak amacıyla hazırlanmıştır.

> Amaç:  
> - Kırılgan `copy selector` / `nth-child` kullanımından kaçınmak  
> - SPA (Vue) tabanlı sayfalarda **state bağımlı DOM**’u doğru anlamak  
> - Selector + sayfa snapshot’larını tek yerde tutmak

---

## Proje Yapısı

```text
.
├── docs/
│   ├── 01_search_page.html      # Arama ekranı DOM snapshot
│   ├── 02_trip_list.html        # Sefer listesi DOM snapshot
│   └── 03_seat_map.html         # Koltuk haritası DOM snapshot
│
├── notes/
│   ├── selectors.md             # Tüm sayfalar için selector defteri
│   └── flow_warnings.md         # Akış/state/SPA uyarıları
│
└── README.md
