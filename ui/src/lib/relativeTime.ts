/**
 * Bir ISO 8601 zaman damgasını Türkçe göreceli metin biçimine dönüştür.
 * Örnek: "2026-09-01T13:55:00Z" → "5 dakika önce"
 *
 * Zaman aralıkları:
 * - < 60s: "az önce"
 * - 1-59 dakika: "{dakika} dakika önce"
 * - 1-23 saat: "{saat} saat önce"
 * - 1+ gün: "{gün} gün önce"
 * - Gelecek zamanlar: "az önce" (graceful fallback)
 * - Geçersiz girdiler: "az önce" (safe fallback)
 */
export function relativeTime(isoString: string): string {
  try {
    const past = new Date(isoString);
    const now = new Date();

    const diffMs = now.getTime() - past.getTime();

    // Negatif veya çok küçük → "az önce" (gelecek zamanlar ve geçersiz)
    if (diffMs < 0) {
      return 'az önce';
    }

    const seconds = Math.floor(diffMs / 1000);
    const minutes = Math.floor(diffMs / (1000 * 60));
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (seconds < 60) {
      return 'az önce';
    } else if (minutes < 60) {
      return `${minutes} dakika önce`;
    } else if (hours < 24) {
      return `${hours} saat önce`;
    } else {
      return `${days} gün önce`;
    }
  } catch (error) {
    // Geçersiz ISO string → safe fallback
    return 'az önce';
  }
}
