import { useEffect, useRef, useState } from 'react';
import { BACKEND_ORIGIN } from '../../lib/backendHealth';
import Card from '../primitives/Card';
import { tokens } from '../../tokens';

// Saga #334: backend/models.py::SearchResultItem ile birebir eşleşir
// (mutlak path İÇERMEZ, bkz. backend/models.py satır 409-416). Diğer
// component'lerin (PlanCard.tsx, ResultCard.tsx) local tip tanımlama
// deseni burada da izlenir — paylaşımlı bir tip-üretim mekanizması yok.
type SearchResultItem = {
  filename: string;
  extension: string;
  modifiedAt: string;
  sizeBytes: number;
};

type Props = {
  sessionId: string;
};

const DEBOUNCE_MS = 300;

export default function SearchPanel({ sessionId }: Props) {
  const [nameContains, setNameContains] = useState('');
  const [extension, setExtension] = useState('');
  const [modifiedAfter, setModifiedAfter] = useState('');
  const [modifiedBefore, setModifiedBefore] = useState('');
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Saga #334 (AC-3): App.tsx'teki `requestPlan`'ın `latestRequestIdRef`
  // deseninin birebir tekrarı — sadece en son başlatılan isteğin sonucu
  // state'e yazılır, geç dönen eski bir yanıt yeni sonucu ezmez.
  const latestRequestIdRef = useRef(0);

  const hasAnyFilter =
    nameContains.trim() !== '' ||
    extension.trim() !== '' ||
    modifiedAfter.trim() !== '' ||
    modifiedBefore.trim() !== '';

  useEffect(() => {
    if (!hasAnyFilter) {
      // AC-1: hiçbir filtre girilmediyse fetch atılmaz, hint state'ine
      // geri dönülür.
      latestRequestIdRef.current += 1;
      setHasSearched(false);
      setError(null);
      setResults([]);
      return;
    }

    const timer = setTimeout(() => {
      const requestId = ++latestRequestIdRef.current;
      const isStale = () => latestRequestIdRef.current !== requestId;

      fetch(`${BACKEND_ORIGIN}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sessionId,
          nameContains: nameContains || undefined,
          extension: extension || undefined,
          modifiedAfter: modifiedAfter || undefined,
          modifiedBefore: modifiedBefore || undefined,
        }),
      })
        .then(async (response) => {
          if (isStale()) return;
          if (!response.ok) {
            // Saga #334 red-team bulgusu: atdd.md Davranış Sözleşmesi
            // tablosundaki 3 ayrı hata durumu (422/410/diğer) burada
            // ayrıştırılır; backend'in `detail` alanı okunur.
            if (response.status === 422) {
              const body = await response.json().catch(() => null);
              if (isStale()) return;
              setError(
                typeof body?.detail === 'string' && body.detail
                  ? body.detail
                  : 'Arama sırasında bir hata oluştu.',
              );
            } else if (response.status === 410) {
              setError('Seçili klasör artık mevcut değil');
            } else {
              setError('Arama sırasında bir hata oluştu.');
            }
            setResults([]);
            setHasSearched(true);
            return;
          }
          const body = await response.json();
          if (isStale()) return;
          setError(null);
          setResults(Array.isArray(body?.results) ? body.results : []);
          setHasSearched(true);
        })
        .catch(() => {
          if (isStale()) return;
          setError('Sunucuya ulaşılamadı. Lütfen tekrar deneyin.');
          setResults([]);
          setHasSearched(true);
        });
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, nameContains, extension, modifiedAfter, modifiedBefore, hasAnyFilter]);

  return (
    <Card className="search-panel" data-testid="search-panel" aria-label="Dosya arama paneli">
      <style>{`
        .search-panel {
          padding: 12px 16px;
        }
        .search-panel-filters {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .search-panel-filters label {
          font-size: ${tokens.fontSize.small};
          color: ${tokens.colors.textDark};
          margin-bottom: 4px;
        }
        .search-panel-input {
          border: 1px solid ${tokens.colors.border};
          border-radius: ${tokens.radius.default};
          padding: 8px 12px;
          font-size: ${tokens.fontSize.base};
          box-sizing: border-box;
        }
        .search-panel-hint,
        .search-panel-empty {
          color: ${tokens.colors.textSecondary};
          font-size: ${tokens.fontSize.small};
          margin: 0;
        }
        .search-panel-error {
          color: ${tokens.colors.danger};
          margin: 0;
        }
        .search-panel-results {
          color: ${tokens.colors.textSecondary};
          font-size: ${tokens.fontSize.small};
          margin: 0;
          padding-left: 20px;
        }
      `}</style>

      <div className="search-panel-filters">
        <label htmlFor="search-panel-name">Isim içerir</label>
        <input
          id="search-panel-name"
          type="text"
          className="search-panel-input"
          value={nameContains}
          onChange={(e) => setNameContains(e.target.value)}
        />

        <label htmlFor="search-panel-extension">Uzantı</label>
        <input
          id="search-panel-extension"
          type="text"
          className="search-panel-input"
          value={extension}
          onChange={(e) => setExtension(e.target.value)}
        />

        <label htmlFor="search-panel-modified-after">Şu tarihten sonra değiştirildi</label>
        <input
          id="search-panel-modified-after"
          type="text"
          className="search-panel-input"
          value={modifiedAfter}
          onChange={(e) => setModifiedAfter(e.target.value)}
        />

        <label htmlFor="search-panel-modified-before">Şu tarihten önce değiştirildi</label>
        <input
          id="search-panel-modified-before"
          type="text"
          className="search-panel-input"
          value={modifiedBefore}
          onChange={(e) => setModifiedBefore(e.target.value)}
        />
      </div>

      {!hasAnyFilter && <p className="search-panel-hint" data-testid="search-panel-hint">Aramak için bir filtre girin</p>}

      {error && (
        <p className="search-panel-error" data-testid="search-panel-error" role="alert">
          {error}
        </p>
      )}

      {!error && hasAnyFilter && hasSearched && results.length === 0 && (
        <p className="search-panel-empty" data-testid="search-panel-empty">Sonuç bulunamadı</p>
      )}

      {!error && results.length > 0 && (
        <ul className="search-panel-results" data-testid="search-panel-results">
          {results.map((item) => (
            <li key={item.filename}>
              <span>{item.filename}</span>
              <span>{item.extension}</span>
              <span>{item.modifiedAt}</span>
              <span>{item.sizeBytes}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
