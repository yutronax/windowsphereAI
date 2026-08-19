# Refaktör: `_parse_search_date` ortak yardımcı fonksiyon

## Ne değiştirildi
`backend/main.py` içinde `search_endpoint()` (`/api/search`) ve `start_search_scan()`
(`/api/search/scan`) fonksiyonlarının ikisinde de birebir tekrarlanan
`modifiedAfter`/`modifiedBefore` ISO 8601 parse + naive→UTC normalizasyon bloğu
(~20 satır x 2), modül seviyesinde tek bir yardımcı fonksiyona çıkarıldı:

```python
def _parse_search_date(value: str | None, field_name: str) -> dt.datetime | None:
    if value is None:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} geçersiz ISO 8601 formatı: '{value}'",
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed
```

`get_session_for_search()`'in hemen altına eklendi. Her iki endpoint artık:

```python
modified_after = _parse_search_date(payload.modifiedAfter, "modifiedAfter")
modified_before = _parse_search_date(payload.modifiedBefore, "modifiedBefore")
```

şeklinde çağırıyor. Hata mesajı formatı, status kodu (422) ve
naive→UTC normalizasyon davranışı birebir korundu — sadece kod tekrarı
kaldırıldı, davranış değişmedi.

## Neden
İki endpoint aynı ~20 satırlık parse/normalizasyon mantığını harfiyen
kopyalamıştı (kod tekrarı / DRY ihlali). Gelecekte bu mantıkta bir değişiklik
(örn. yeni bir format desteği) gerektiğinde iki yerde ayrı ayrı güncelleme
riski vardı.

## Kapsam dışı
- Test dosyalarına dokunulmadı.
- Başka hiçbir fonksiyon/dosya değiştirilmedi.
- `search_files`, `_run_scan`, session/allowed_root doğrulama mantığı aynen kaldı.

## Doğrulama — pytest sonucu
```
.venv/Scripts/python.exe -m pytest backend/tests/ -v
...
================= 359 passed, 4 skipped, 5 warnings in 21.07s =================
```
Tam yeşil: 359 passed, 4 skipped, 0 failed (beklenen sonuçla birebir eşleşiyor).

## Temizlik kontrolü (kalıntı taraması)
`grep -rn "fromisoformat" backend/main.py` → sadece `_parse_search_date` içinde
tek bir çağrı bulundu. Eski tekrar eden bloklardan kalıntı yok, ek bir
temizlik görevi gerekmedi.

## Not — Saga görev kaydı
Bu görev için proje kökünde (windows-ai-files) bir saga MCP aracı veya
proje-özel saga mekanizması bulunamadı (saga skill'i sadece `obss_project`
altında mevcut). Bu nedenle kod değişikliğinden önce bir saga görev kaydı
oluşturulamadı — bu bir açık nokta olarak aşağıda not edildi.

## Open questions
- windows-ai-files projesi için saga görev takibi hangi mekanizmayla
  yapılmalı (MCP aracı mı eklenecek, yoksa obss_project'teki gibi ayrı bir
  `.saga` dizini mi kurulacak)? Netleşmedi, varsayımla doldurulmadı.
