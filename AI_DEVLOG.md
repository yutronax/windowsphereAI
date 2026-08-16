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
