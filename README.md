# Imager (Local Duplicate Organizer + Date Fixer)

Yerel (offline) çalisan, medya odakli bir dosya düzenleme aracidir.

- **Duplicate Organizer**: Ayni içerige sahip dosyalari gruplar, "orijinal" seçtirir, sadece seçilenleri export klasörüne kopyalar.
- **Date Fixer**: EXIF / filename / manual modlarinda tarih düzeltme yapar, degisiklikleri export kopyalara uygular.

> Tasarim hedefi: **kaynak dosyalari silmeden, güvenli export akisi**.

---

## Özellikler

- Duplicate tespiti: boyut + `xxhash` içerik hash
- Görsel + video thumbnail (video için ffmpeg)
- Hover büyük önizleme (videoda autoplay)
- `Mark Recommended` ile grup basina önerilen orijinal seçimi
- Büyük veri için parça parça yükleme (pagination/load more)
- Date Fixer EXIF karar motoru:
  - EXIF öncelikli
  - EXIF yili filename yilindan ilerideyse filename tarihi esas
  - EXIF yoksa filename tarihi EXIF'e kalici yazilir
  - EXIF + filename tarih yoksa dosya `SKIP`
- Onay akisi: `Cancel + Approve` (iki sayfada da)
- Islem sirasinda görünür `Processing...` göstergesi

---

## Güvenlik ve Gizlilik

Bu proje GitHub'a açik paylasim öncesi su önlemleri içerir:

1. **Localhost erisim kisiti**
- API yalnizca `127.0.0.1 / ::1 / localhost` isteklerini kabul eder.
- Dis agdan erisim engellenir.

2. **Izinli kök dizin kontrolü**
- `preview`, `thumbnail`, `metadata/apply` endpoint'leri yalnizca taranmis kök klasör altindaki dosyalara izin verir.
- Keyfi path ile dosya okuma/yazma engellenir.

3. **Kaynak dosya güvenligi**
- Kaynak dosyalar silinmez.
- Islemler export kopya üzerinde yapilir.

4. **Overwrite korumasi**
- Export sirasinda orijinal dosya adi korunur.
- Hedefte isim çakisirsa güvenli suffix (`(2)`, `(3)`) eklenir.

5. **Git'e hassas/yerel veri gönderimini engelleme**
- `.gitignore` ile `venv/`, `files.db`, `memory-bank/thumb-cache/` vb. disarida birakilir.

---

## Gereksinimler

- Python 3.10+
- Windows (ana hedef ortam)
- ffmpeg (video thumbnail için)

---

## Kurulum

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

ffmpeg kontrolü:

```powershell
ffmpeg -version
```

---

## Çalistirma

### Seçenek 1 (önerilen)

```powershell
run_app.bat
```

### Seçenek 2

```powershell
venv\Scripts\python -m uvicorn app.main:app --reload
```

Ardindan tarayici:

- `http://127.0.0.1:8000`

---

## Kullanim

### 1) Duplicate Organizer

1. Source klasörü gir, `Start Scan`
2. Istersen `Mark Recommended`
3. Grupta gerekli düzeltmeleri yap
4. Export hedef klasörü gir
5. `Export Selected` -> `Approve`

### 2) Date Fixer

1. `Date Fixer` sayfasina geç
2. Source klasörü gir, `Scan`
3. Mod seç (`EXIF`, `Filename`, `Manual`)
4. Export hedef klasörü gir
5. `Export & Fix Files` -> `Approve`

Notlar:
- `SKIP` etiketli dosyalar mevcut moda göre islenemez ve atlanir.
- Video dosyalarda EXIF yazimi yapilmaz; tarih dosya sistemi zamanina uygulanir.

---

## API Özeti

- `POST /api/scan`
- `GET /api/duplicates_page`
- `POST /api/mark_original/{file_id}`
- `POST /api/recommend_originals`
- `POST /api/commit_cleanup`
- `POST /api/metadata/scan`
- `GET /api/metadata/preview`
- `GET /api/metadata/thumbnail`
- `POST /api/metadata/apply`

---

## Performans Notlari

- Duplicate listesi kademeli yüklenir.
- Thumbnail'ler cache'lenir (`memory-bank/thumb-cache`).
- Çok büyük klasörlerde ilk tarama süresi dogal olarak uzayabilir.

---

## Hata Giderme

### Video dosyada "EXIF write failed" hatasi
Yeni sürümde video dosyalarda EXIF yazimi denenmez. Eger eski davranis görürsen:

1. Sunucuyu kapat/aç
2. Tarayicida `Ctrl+F5` yap

### `403 Path is not in allowed scanned roots`
Önce ilgili klasörü uygulama içinden tekrar `Scan` et.

---

## Ekran Görüntüleri

> Bu bölüm bilerek bos birakilmistir. Screenshot'lari eklemek için asagidaki basliklari kullanabilirsiniz.

### Duplicate Organizer

<!-- screenshot buraya -->

### Date Fixer

<!-- screenshot buraya -->

### Mark Recommended Akisi

<!-- screenshot buraya -->

### Security / Privacy Notlari

<!-- screenshot buraya -->

---

## Lisans

Lisans bilgisini burada belirtin.
