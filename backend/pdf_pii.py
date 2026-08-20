"""Saga #333: PDF metni tarayarak PII (TC kimlik no, IBAN) tespiti.

Bu modül, metin katmanlı bir PDF'in içeriğini tarar, resmi TC kimlik no
checksum algoritmasını geçen 11 haneli dizeler ve TR+24 hane IBAN
kalıplarını bulup, her biri için RedactionRegion listesi önerir (AC-1).

AC-S1: Ham TC kimlik no/IBAN değerleri yanıta, loga veya hata mesajına
YAZILMAZ — sadece koordinatlar döner.

AC-S2: Regex kalıpları sabit uzunluklu (\d{11}, TR\d{24}) — ReDoS riski yok.
"""

import re
from pathlib import Path

from pypdf import PdfReader

from backend.models import RedactionRegion


# Modül seviyesinde sabit-uzunluklu regex kalıpları (AC-S2)
_TC_KIMLIK_NO_PATTERN = re.compile(r"\b\d{11}\b")
_IBAN_PATTERN = re.compile(r"\bTR\d{24}\b")


def _is_valid_tc_kimlik_no(digits: str) -> bool:
    """TC kimlik numarası checksum doğrulaması.

    Resmi Türkiye TC kimlik no algoritması:
    - 11 hane, ilk hane 0 olamaz.
    - 10. hane: (1,3,5,7,9. hanelerin toplamı × 7 − 2,4,6,8. hanelerin toplamı) mod 10.
    - 11. hane: (ilk 10 hanenin toplamı) mod 10.

    Kaynak: https://www.nvi.gov.tr/ (resmi TC Nüfus ve Vatandaşlık İşleri Genel Müdürlüğü)
    """
    if len(digits) != 11:
        return False

    # İlk hane 0 olamaz
    if digits[0] == "0":
        return False

    # Hepsi rakam olmalı
    if not digits.isdigit():
        return False

    # Checksum kontrolleri
    # 10. hane kontrolü (indeks 9)
    odd_sum = sum(int(digits[i]) for i in [0, 2, 4, 6, 8])  # 1, 3, 5, 7, 9. haneler
    even_sum = sum(int(digits[i]) for i in [1, 3, 5, 7])  # 2, 4, 6, 8. haneler
    tenth_digit = (odd_sum * 7 - even_sum) % 10

    if int(digits[9]) != tenth_digit:
        return False

    # 11. hane kontrolü (indeks 10)
    total_sum = sum(int(digits[i]) for i in range(10))  # İlk 10 hanenin toplamı
    eleventh_digit = total_sum % 10

    if int(digits[10]) != eleventh_digit:
        return False

    return True


def detect_pii(pdf_path: Path) -> list[RedactionRegion]:
    """PDF'te PII (TC kimlik no, IBAN) bulur ve RedactionRegion listesi döner.

    Visitor_text callback tabanlı yaklaşım: her metin parçasının PDF nokta-uzayındaki
    konumunu (tm[4], tm[5]) topla, regex eşleşmelerini o konumlarla ilişkilendir,
    gerçek bounding box hesapla.

    Args:
        pdf_path: Taranacak PDF dosyasının yolu.

    Returns:
        Her biri bir PII eşleşmesinin konumunu temsil eden RedactionRegion'ların listesi.
        Eşleşen değerler ASLA döndürülen objede yer almaz (AC-S1).

    Raises:
        Bozuk PDF, açılamayan dosya gibi durumlar pypdf exception'ını
        yukarı fırlatır (endpoint tarafından 422'ye çevrilir).
    """

    # PDF'i aç
    reader = PdfReader(str(pdf_path))

    regions: list[RedactionRegion] = []

    for page_idx, page in enumerate(reader.pages):
        page_number = page_idx + 1  # 1-indexed (AC gereksinimi)

        # Sayfa mediabox'ından boyutları al (AC-5: sınır kontrolü için)
        mediabox = page.mediabox
        page_width_pt = float(mediabox.width)
        page_height_pt = float(mediabox.height)

        # Visitor callback ile metin parçalarını topla
        full_text = ""
        text_fragments: list[dict] = []

        def visitor_text(text: str, cm, tm, font_dict, font_size):
            """Visitor callback — her metin parçasının konumunu topla."""
            nonlocal full_text
            # Boş metin parçalarını atla
            if not text:
                return
            # Ayraç ekle (ilk fragment hariç) - fragment sınırlarının
            # regex'te yanlışlıkla birleşip sahte PII eşleşmesi üretmesini
            # önler (red-team bulgusu: iki alakasız metin parçasının
            # bitişik rakamları tek bir 11-haneli/IBAN dizisi gibi
            # eşleşebiliyordu).
            if full_text:
                full_text += " "
            fragment_start_offset = len(full_text)
            full_text += text
            # tm (text matrix) = [a, b, c, d, e, f]
            # e = x koordinatı, f = y koordinatı (PDF nokta uzayı, sol-alt kokenli)
            x = tm[4] if len(tm) > 4 else 0
            y = tm[5] if len(tm) > 5 else 0
            size = font_size if font_size else 12
            text_fragments.append({
                "text": text,
                "x": float(x),
                "y": float(y),
                "size": float(size),
                "start_offset": fragment_start_offset,
                "end_offset": fragment_start_offset + len(text),
            })

        # Sayfadan metni ve konum bilgisini çıkar
        try:
            page.extract_text(visitor_text=visitor_text)
        except Exception:
            # Metin çıkarma başarısız olursa bu sayfa atlanır
            # (taranmış/OCR gereken PDF, kapsam dışı AC-2 ile tutarlı)
            continue

        if not full_text or not text_fragments:
            # Bu sayfada metin yok
            continue

        # Tam metin üzerinde TC kimlik no ve IBAN kalıplarını ara
        for match in _TC_KIMLIK_NO_PATTERN.finditer(full_text):
            matched_str = match.group()
            if not _is_valid_tc_kimlik_no(matched_str):
                # Checksum tutmuyor, PII değil (AC-3, yanlış-pozitif önleme)
                continue

            start_offset = match.start()
            end_offset = match.end()

            # Eşleşmenin offset aralığıyla çakışan metin parçalarını bul
            region = _calculate_bounding_box_from_fragments(
                text_fragments,
                start_offset,
                end_offset,
                page_width_pt,
                page_height_pt,
            )
            if region is not None:
                regions.append(RedactionRegion(
                    page=page_number,
                    x0=region["x0"],
                    y0=region["y0"],
                    x1=region["x1"],
                    y1=region["y1"],
                ))

        # IBAN kalıplarını ara
        for match in _IBAN_PATTERN.finditer(full_text):
            start_offset = match.start()
            end_offset = match.end()

            region = _calculate_bounding_box_from_fragments(
                text_fragments,
                start_offset,
                end_offset,
                page_width_pt,
                page_height_pt,
            )
            if region is not None:
                regions.append(RedactionRegion(
                    page=page_number,
                    x0=region["x0"],
                    y0=region["y0"],
                    x1=region["x1"],
                    y1=region["y1"],
                ))

    return regions


def _calculate_bounding_box_from_fragments(
    text_fragments: list[dict],
    start_offset: int,
    end_offset: int,
    page_width_pt: float,
    page_height_pt: float,
) -> dict | None:
    """Eşleşmenin offset aralığıyla çakışan metin parçalarından bounding box hesapla.

    AC-5: Sayfa sınırlarını aşan kutuları at.
    """

    if not text_fragments:
        return None

    # Eşleşeme aralığıyla çakışan metin parçalarını bul
    covering_fragments = []
    for frag in text_fragments:
        frag_start = frag["start_offset"]
        frag_end = frag["end_offset"]

        # Parça eşleşme aralığıyla örtüşüyor mu?
        if frag_end > start_offset and frag_start < end_offset:
            covering_fragments.append(frag)

    if not covering_fragments:
        # Hiçbir parça eşleşmeyle çakışmıyor — eşleşmeyi atla
        return None

    # Bounding box hesapla
    x_min = min(frag["x"] for frag in covering_fragments)
    y_min = min(frag["y"] for frag in covering_fragments)
    # Tahmini karakter genişliği: font_size * 0.6 (yaklaşık)
    x_max = max(
        frag["x"] + len(frag["text"]) * frag["size"] * 0.6
        for frag in covering_fragments
    )
    y_max = max(frag["y"] + frag["size"] for frag in covering_fragments)

    # AC-5: Sayfa sınırlarını aşma kontrolü
    epsilon = 0.5
    if (
        x_min < -epsilon
        or y_min < -epsilon
        or x_max > page_width_pt + epsilon
        or y_max > page_height_pt + epsilon
    ):
        # Geçersiz bölge, atla
        return None

    # Koordinatları doğru sayfa sınırlarına sınırla (negatif değer yok)
    x_min = max(0, x_min)
    y_min = max(0, y_min)
    x_max = min(page_width_pt, x_max)
    y_max = min(page_height_pt, y_max)

    # x0 < x1 ve y0 < y1 garantisi
    if x_max <= x_min or y_max <= y_min:
        return None

    return {
        "x0": x_min,
        "y0": y_min,
        "x1": x_max,
        "y1": y_max,
    }
