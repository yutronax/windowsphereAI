---
task_slug: requirements-txt-pdf-kutuphane-secimi
priority: high
coverage_target: "yok (bağımlılık/tooling task, davranış kodu yok)"
performance_target: "yok"
test_strategy: "unit (requirements.txt'in gerçekten pip install ile kurulabildiğini doğrulayan bir smoke test)"
affected_modules:
  - requirements.txt (yeni)
saga_task_id: 303
epic_id: 29
---

# ATDD — requirements.txt + PDF Merge/Split Kütüphane Seçimi (Saga #303)

## Goal
Projenin bir `requirements.txt`'i yok (mevcut bağımlılıklar sadece
kurulu, dosyaya yazılı değil). Bu task hem eksikliği kapatıyor hem de
gelecekteki merge/split task'larının (Saga #304/#305) kullanacağı PDF
kütüphanesini seçiyor.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: pypdf mi PyMuPDF mi?** Cevap: **pypdf.** Proje hafızasında
("Ürünleştirme Planı") windows-ai-files'ın ticari bir lisans modeliyle
SATILMASI planlanıyor — PyMuPDF'in AGPL-3.0 lisansı, kaynak kodu
açmadan ticari dağıtım yapan bir masaüstü uygulaması için gerçek bir
hukuki risk taşır (AGPL, ağ üzerinden sunulan/dağıtılan türev
çalışmaların kaynak kodunun da açılmasını zorunlu kılar). `pypdf` saf
Python + BSD benzeri (MIT) lisanslı, ticari kullanım kısıtı yok. Hız
farkı (PyMuPDF daha hızlı) MVP ölçeğindeki merge/split işlemleri için
gözlemlenebilir bir kullanıcı sorunu değil — somut bir performans
kanıtı yok. (saga-oto tarafından otomatik seçildi — kod tabanında
aksini gösteren somut bir kanıt yoksa güvenli/kısıtsız lisans varsayılan
tercih, proje hafızasındaki ticari satış planıyla tutarlı)

**S2: requirements.txt'e hangi bağımlılıklar girmeli?** Cevap: Backend'in
ŞU AN kurulu ve `backend/` altında gerçekten import edilen paketler:
`fastapi`, `uvicorn`, `sqlalchemy`, `openai`, `pydantic`. Test
bağımlılıkları (`pytest`, `pytest-mock`) ayrı bir
`requirements-dev.txt`e mi yoksa aynı dosyaya mı — dar kapsam: AYNI
dosyaya, ayrı bir dev-dosyası İCAT ETMEK bu task'ın kapsamını aşar
(YAGNI, proje şu an tek bir ortamda geliştiriliyor). `pypdf`, merge/
split task'ları henüz kod yazmasa da BURADA eklenir (kütüphane kararı
bu task'ın konusu). PyMuPDF/pypdfium2 (ortamda kurulu ama KULLANILMAYACAK)
requirements.txt'e EKLENMEZ — sadece gerçekten kullanılacak/import
edilecek paketler dosyada yer alır. (saga-oto tarafından otomatik
seçildi)

**S3: Versiyon pinleme nasıl olmalı?** Cevap: Ortamda kurulu GERÇEK
versiyonlar `==` ile pinlenir (`pip freeze`'den okunan gerçek sürümler)
— aralık (`>=`) belirsizlik yaratır, mevcut projenin diğer hiçbir
yerinde (ör. `ui/package.json`) aralık kullanılmıyor (tam sürümler
sabit). (saga-oto tarafından otomatik seçildi — proje konvansiyonuna
tutarlılık)

## Kabul Kriterleri
1. **AC-1 (kritik):** `requirements.txt` var, `backend/` altında
   gerçekten import edilen tüm paketleri (fastapi, uvicorn, sqlalchemy,
   openai, pydantic, pytest, pytest-mock, pypdf) pinlenmiş sürümlerle
   içeriyor.
2. **AC-2 (kritik):** `pip install -r requirements.txt` temiz bir
   sanal ortamda (veya `--dry-run`/gerçek kurulum) hatasız çalışıyor.
3. **AC-3 (yüksek):** `pypdf` seçimi ve gerekçesi (lisans) bu ATDD'de
   VE `AI_DEVLOG.md`'de açıkça belgeleniyor — gelecekteki bir
   geliştirici "neden PyMuPDF değil" sorusunu tekrar sormasın.

## Riskler / Varsayımlar / Bilinmeyenler
- `pypdf`in merge/split için gerçek API yeterliliği (Saga #304/#305'te
  doğrulanacak) — bu task sadece kütüphane SEÇİMİni yapıyor, gerçek
  kullanım kodu yazmıyor.
- Ortamda PyMuPDF/pypdfium2'nin NEDEN kurulu olduğu bilinmiyor (başka
  bir araç/bağımlılık zinciri getirmiş olabilir) — requirements.txt'e
  eklenmedikleri için proje bunlara bağımlı OLMAYACAK, ama ortamda
  kurulu kalmaları zararsız.

## Test Stratejisi
`pip install -r requirements.txt` gerçek bir geçici sanal ortamda
çalıştırılıp hatasız bittiği doğrulanır (otomatik test değil, bash
smoke-check — Python bağımlılık dosyaları için "unit test" kavramı
uygulanmıyor, `verify` adımında gerçek komutla doğrulanacak).
