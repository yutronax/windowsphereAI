# AI_DEVLOG.md — windows-ai-files

## ilk-acilis-klasor-secimi-ekrani (Saga #250, epic #23)

**Zorluk — Codex kotası tükendi task ortasında.** Tooling scaffold'u yazdıktan
sonra Codex (`gpt-5.6-terra`) kullanım limitine ulaştı (Eylül 15'e kadar
kullanılamaz durumda). Kalan düzeltmeler (test cleanup/matcher kaydı, 3 e2e
hatası, red-team bulguları) `efektor` subagent'ına devredildi — pipeline'ın
öngördüğü yedek yol (bkz. proje hafızası "Copilot → Codex Geçişi").

**Bulunan bug — CORS/relative-path fetch (red-team, HIGH).** Frontend
`fetch('/api/health')` gibi göreli yollar kullanıyordu; backend'de CORS
middleware yoktu. Bu, 17 testin tamamı backend'i mock'ladığı için hiç
yakalanmamıştı — paketlenmiş Tauri uygulamasında webview origin'i
(`tauri://localhost`) ile FastAPI sidecar origin'i (`127.0.0.1:8000`) farklı
olacağından, onboarding ekranı gerçek kullanıcıda sonsuza kadar
"Başlatılıyor…" da takılı kalabilirdi. Düzeltme: mutlak URL + açık CORS
origin listesi + gerçek FastAPI `TestClient` entegrasyon testi eklendi
(`backend/tests/test_main_integration.py`) — atdd.md'nin vaat ettiği %30
integration coverage'ı artık gerçekten mock'suz karşılıyor.

**Bilinçli kapsam kararı.** Tauri/Rust iskeleti (`src-tauri/`) ve `unit_test`
tarzı ikinci bir test klasörü bu task'tan bilinçli olarak çıkarıldı — bu task
yalnızca `docs/DESIGN_DECISIONS.md`'nin frontend/backend katmanlarını
gerçekten çalışır kılmayı hedefledi, native masaüstü paketleme ayrı bir task.

## onboarding-istek-placeholder (Saga #254, epic #23)

**Zorluk — Codex kotası task başlamadan önce tamamen doluydu.** #250'de
kota task ortasında tükenmişti (yukarı bakınız); bu task'ta ise ilk
`write_tests()` çağrısı anında `ERROR: You've hit your usage limit... try
again at Sep 15th, 2026` ile başarısız oldu — hiç Codex bütçesi
harcanamadı. Kullanıcıya soruldu (dar kapsam: tek dosya, ~5 satır
implementasyon), kullanıcı onayıyla testler VE implementasyon istisnai
olarak Claude (ana asistan) tarafından yazıldı — normal test-copilot/
code-copilot kuralı ("her satır Codex'ten gelir") bu tek task için bilinçli
olarak esnetildi. Riski azaltmak için: red-team incelemesi `obss-red-team`
subagent'ı ile bağımsız çalıştırıldı ve gerçek `git diff`'i code_diff.md/
test_diff.md iddialarıyla birebir karşılaştırdı (verdict: approve,
ready_to_commit: true).

**Kalıcı öneri (red-team'den, bu task'ta uygulanmadı).** Placeholder metni
("Bu klasördeki PDF'leri tarihe göre sırala") 3 dosyada literal string
olarak tekrarlanıyor (component, unit test, e2e test). Saga #257/#258 veya
i18n bu ekrana dokunursa, ortak bir sabite (`PLACEHOLDER_TEXT` gibi)
çıkarılması önerilir — bu task'ın dar kapsamı için gerekli görülmedi.

## bos-istek-engelleme (Saga #255, epic #23)

**Codex kotası hâlâ dolu (2026-09-15'e kadar).** #254'teki gibi, `saga` skill
Bölüm C override'ı uygulandı: testler VE implementasyon Claude (ana asistan)
tarafından doğrudan yazıldı, `test-copilot`/`code-copilot` (Codex) çağrılmadı.
Bağımsız doğrulama yine `obss-red-team` subagent'ı ile yapıldı — gerçek
`git diff`'i code_diff.md/test_diff.md iddialarıyla karşılaştırdı, 21 unit +
16 e2e testi ve `tsc --noEmit`'i kendi bağlamında yeniden çalıştırıp PASS
buldu (verdict: ready_to_commit: evet).

**CSS özgüllük tuzağı önceden öngörüldü ve çözüldü.** `.onboarding-textarea:focus`
(odak kenarlığı, mavi) ile yeni `.onboarding-textarea.has-error` (hata
kenarlığı, kırmızı) aynı CSS özgüllüğüne (0,2,0) sahipti — hangisinin
kazanacağı sadece stylesheet'teki tanım sırasına bağlı kalırdı (kırılgan).
`.onboarding-textarea.has-error:focus` (0,3,0) eklenerek hata durumunun
odaklanmışken de kırmızı kalması garanti edildi; red-team bunu elle
doğrulayıp doğru bulduğunu teyit etti.

**Codex vision-test de kota nedeniyle kullanılamadı.** Standart `vision-test`
skill'i de Codex'e bağımlı olduğu için, görsel doğrulama Codex vision yerine
gerçek Vite dev server + Playwright ile alınan bir ekran görüntüsünün
(`artifacts/bos-istek-engelleme/empty_request_error_state.png`) Claude
tarafından doğrudan incelenmesiyle yapıldı — bu istisna verify_report.md'de
açıkça not edildi.

**Kalıcı öneri (red-team'den, bu task'ta uygulanmadı — low severity).**
(1) `trim()` zero-width Unicode karakterleri (ör. U+200B) temizlemiyor,
sadece bu tür karakterlerden oluşan bir istek teknik olarak "boş değil"
sayılabilir. (2) `aria-live="polite"` container'ı koşullu mount ediliyor
(her zaman DOM'da olup sadece içeriği değişen bir container yerine) — bazı
ekran okuyucu/tarayıcı kombinasyonlarında duyuru güvenilirliğini
etkileyebilir. İkisi de bu task'ın dar kapsamı (client-side, backend
validasyonu yok) için engelleyici değil, ayrı bir iyileştirme task'ı olarak
değerlendirilebilir.
