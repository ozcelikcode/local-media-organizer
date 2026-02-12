# Product Context

## Problem
Kullanici ayni klasörde çok fazla duplicate medya biriktiriyor. Yanlis dosyayi saklama/silme korkusu var. Ayrica birçok dosyada EXIF eksik veya tutarsiz oldugu için tarih düzenleme güvenilir degil.

## Current Product Behavior
### 1) Duplicate Organizer
- Kaynak klasör taranir, duplicate gruplar çikarilir.
- Kullanici veya `Mark Recommended` ile her grupta orijinal seçilir.
- Export isleminde sadece seçilen orijinaller hedefe kopyalanir.
- Kaynakta silme yapilmaz.

### 2) Date Fixer
- Medya dosyalari listelenir (image + video).
- EXIF/Filename/Manual modlari ile tarih uygulanir.
- Islem export kopyada kalici yapilir.
- Belirsiz dosyalar (`EXIF yok + filename'dan tarih yok`) otomatik skip edilir ve UI'da `SKIP` olarak isaretlenir.

## Critical User Rules (Implemented)
1. EXIF varsa öncelik EXIF.
2. EXIF yili, filename yilindan ilerideyse filename esas alinir.
3. Yil eslesiyorsa EXIF devam eder.
4. Saat/gün yoksa en azindan yil korunur (filename parse precision fallback).
5. EXIF zaten varsa gereksiz overwrite yapilmaz; kural gerektiriyorsa kontrollü overwrite yapilir.

## UX Expectations
- Onay modali iki sayfada da `Cancel + Approve`.
- `Cancel`: islem baslamadan iptal.
- `Approve`: islem baslar ve `Processing...` görünür.
- Büyük listelerde "Daha Fazla Yukle" ile kademeli render.

## Safety Model
- Source klasör read-only kabul edilir.
- Export hedefinde overwrite yok, unique isim üretilir.
- Hiçbir islem kaynak dosya silmez.
