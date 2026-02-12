# Active Context

## Current Focus
- Date Fixer EXIF karar motoru ve modal/processing akisi stabilize edildi.
- Duplicate Organizer performans/pagination ve öneri seçimi çalisir durumda.
- Export isimlendirme politikasi "orijinal isim + çakismada suffix" olarak sabitlendi.

## Recent Changes (Latest)
1. Modal akisi iki sayfada `Cancel + Approve` olarak standardize edildi.
2. `Processing...` görünürlügü Date Fixer'a eklendi.
3. Thumbnail endpoint (cache + video ffmpeg) eklendi ve UI thumbnail'a geçirildi.
4. Duplicate page endpoint + frontend incremental load eklendi.
5. `Mark Recommended` butonu ve backend recommendation endpoint eklendi.
6. EXIF mode logic:
- exif future-year mismatch -> filename override
- precision fallback (datetime/date/year-month/year)
- unresolved -> skip
7. Belirsiz dosyalar UI'da `SKIP` etiketi ile görünür.

## Open Risks / Watchlist
- Çok büyük `thumb-cache` klasörü disk kullanimi artirabilir.
- ffmpeg olmayan sistemlerde video thumbnail basarisiz olur.
- `recommend_originals` çok büyük DB'de tek transaction oldugu için uzun sürebilir.

## Next Suggested Actions
1. Thumbnail cache retention policy (LRU veya max-size cleanup).
2. `recommend_originals` için batch commit/chunking.
3. Date Fixer için backend-side pagination (su an frontend slice).
4. EXIF karar logunu kullaniciya istege bagli export etmek.
