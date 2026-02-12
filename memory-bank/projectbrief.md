# Project Brief

## Project Overview
Yerel çalisan bir medya düzenleme araci:
- Duplicate Organizer: ayni içerikli dosyalari gruplar, kullaniciya "orijinal" seçtirir, export klasörüne güvenli kopyalar.
- Date Fixer: dosya tarih bilgisini EXIF/Filename/Manual kaynaklarina göre export kopyalara uygular.

Sistem "source klasörüne dokunmama" prensibiyle çalisir; kalici degisiklikler export tarafinda yapilir.

## Core Requirements (Current)
1. Local-only çalisma (Windows agirlikli).
2. Duplicate tespiti: boyut + içerik hash (xxhash).
3. Güvenli seçim: grup içinde tek `is_original`.
4. Export güvenligi:
- Kaynak dosyalar silinmez.
- Hedefte orijinal dosya adi korunur.
- Isim çakisirsa yalnizca güvenli suffix (`(2)`, `(3)`) eklenir.
5. Date Fixer EXIF kurallari:
- EXIF öncelikli.
- EXIF yili filename yilindan ileri ise filename tarihi esas alinir.
- EXIF yoksa filename tarihi EXIF'e kalici yazilir.
- EXIF ve filename'dan tarih çikarilamiyorsa dosya skip olur.
6. Büyük veri performansi:
- Duplicate listesi backend paged endpoint ile parçali yüklenir.
- Thumbnail cache kullanilir (image + video).

## Non-Functional Goals
- Veri kaybini engellemek (overwrite yok, delete yok).
- Binlerce grup/dosyada UI freeze riskini azaltmak.
- Deterministic ve izlenebilir karar mekanizmasi.

## Success Criteria
- Duplicate/Date export akislari hatasiz tamamlanir.
- "Mark Recommended" ile gruplarin tamami tek aksiyonda isaretlenir.
- Video ve görsel preview stabil çalisir.
- EXIF karar motoru yil çakisma kuralini dogru uygular.
