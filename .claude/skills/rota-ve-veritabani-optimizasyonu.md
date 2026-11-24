---
name: rota-ve-veritabani-optimizasyonu
description: Konteyner doluluk verilerine göre dinamik toplama rotası hesaplar ve veritabanı şemasını yönetir.
---
1. Sadece doluluk oranı >= %80 olan veya kritik alarm veren konteynerleri aktif rotaya dahil et.
2. En yakın komşu (Nearest Neighbor) veya mesafe matrisi mantığıyla toplam kilometre ve yakıt tasarrufu metriğini hesapla.
3. Veritabanı tablolarını (`bins`, `vehicles`, `routes`, `collections`) hem Bulut PostgreSQL hem de MS SQL uyumlu SQLAlchemy modelleriyle kurgula.
