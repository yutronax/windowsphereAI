import { useState } from 'react';

import { BACKEND_ORIGIN } from '../../lib/backendHealth';

export type TransactionResult = {
  fileCount: number;
  destinationFolders: string[];
  status: 'completed' | 'partial' | 'failed';
  // Saga #301: sadece transactionId gerekli — allowedRoot artık backend'de
  // Transaction'a kaydedilir, istemciden gönderilmez. selectedFolder alanı
  // tip uyumluluğu için kalır ama revert akışında artık KULLANILMAZ.
  transactionId?: number;
  selectedFolder?: string;
};

type Props = {
  result: TransactionResult;
};

// Saga #317: GET /api/transactions'in dondurdugu preview sekli - backend'in
// backend/models.py::TransactionPreview/TransactionPreviewFile'iyla AYNI
// alanlar. SADECE dosya adi tasir (Saga #283 ilkesi), tam path YOK.
type PreviewFile = {
  name: string;
  before: string | null;
  after: string | null;
  status: string;
  available?: boolean;
  reason?: string | null;
};

type Preview = {
  files: PreviewFile[];
  truncated: boolean;
  total_count: number;
  empty: boolean;
  available?: boolean;
  reason?: string | null;
};

type PreviewLoadState = 'idle' | 'loading' | 'loaded' | 'error';

const STATUS_TEXT: Record<TransactionResult['status'], string> = {
  completed: 'İşlem tamamlandı.',
  partial: 'İşlem kısmen tamamlandı.',
  failed: 'İşlem tamamlanamadı.',
};

type RevertState = 'idle' | 'confirming' | 'reverting' | 'reverted' | 'revert_failed' | 'error';

export default function ResultCard({ result }: Props) {
  const [revertState, setRevertState] = useState<RevertState>('idle');
  const [previewState, setPreviewState] = useState<PreviewLoadState>('idle');
  const [preview, setPreview] = useState<Preview | null>(null);
  const hasFolders = result.destinationFolders.length > 0;

  // Saga #317: hover'da önizleme YALNIZCA bir kez, lazy olarak yüklenir —
  // ayrı/yeni bir endpoint YOK, mevcut GET /api/transactions listesi
  // içinden kendi transactionId'sine karşılık gelen `preview` alanı
  // bulunur (AC-2: "ayrı bir endpoint çağrısı gerekmez" — yeni bir
  // endpoint eklenmedi, mevcut liste endpoint'i yeniden kullanıldı).
  async function handleHoverLoadPreview() {
    if (result.transactionId === undefined) return;
    if (previewState !== 'idle') return;
    setPreviewState('loading');
    try {
      const response = await fetch(`${BACKEND_ORIGIN}/api/transactions`);
      if (!response.ok) {
        setPreviewState('error');
        return;
      }
      const body: Array<{ id: number; preview: Preview }> = await response.json();
      const own = body.find((entry) => entry.id === result.transactionId);
      if (own === undefined) {
        setPreviewState('error');
        return;
      }
      setPreview(own.preview);
      setPreviewState('loaded');
    } catch {
      setPreviewState('error');
    }
  }
  // Saga #301: `transactionId` eksikse istemci geri alma isteği
  // OLUŞTURAMAZ — buton hiç gösterilmez. Asıl güvenlik sınırı backend'in
  // kendisinde (server tarafında kaydedilen allowed_root + committed-only
  // kontrolü), bu sadece bir istemci tarafı UX kolaylığı.
  const canShowRevert = result.transactionId !== undefined;

  async function handleConfirmRevert() {
    if (result.transactionId === undefined) return;
    // Red-team bulgusu (Saga #295): butonun `disabled` olması normalde
    // ikinci bir tıklamayı engeller, ama bu SADECE React'in re-render'ı
    // yeterince hızlı gerçekleştiğinde işe yarar — programatik çift
    // dispatch/düşük performanslı cihaz senaryosunda `handleConfirmRevert`
    // ikinci kez çağrılabilir. Bu erken çıkış, render zamanlamasına
    // GÜVENMEDEN aynı transaction için iki eşzamanlı isteği engeller.
    if (revertState === 'reverting') return;
    setRevertState('reverting');
    try {
      const response = await fetch(`${BACKEND_ORIGIN}/api/transactions/${result.transactionId}/revert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (!response.ok) {
        setRevertState('error');
        return;
      }
      const body: { status: string } = await response.json();
      setRevertState(body.status === 'reverted' ? 'reverted' : 'revert_failed');
    } catch {
      setRevertState('error');
    }
  }

  return (
    <section
      className="result-card"
      data-testid="result-card"
      aria-label="İşlem sonucu"
      onMouseEnter={handleHoverLoadPreview}
    >
      <style>{`
        .result-card {
          border: 1px solid #E5E7EB;
          border-radius: 12px;
          padding: 12px 16px;
          margin-top: 8px;
          background-color: #FAFAFA;
        }
        .result-card-file-count {
          font-weight: 600;
          margin: 0 0 8px;
        }
        .result-card-folders {
          margin: 0;
          padding-left: 20px;
          color: #4B5563;
          font-size: 14px;
        }
        .result-card-empty-folders {
          margin: 0;
          color: #4B5563;
          font-size: 14px;
        }
        .result-card-status-text {
          color: #4B5563;
          font-size: 14px;
          margin-top: 8px;
        }
        .result-card-status-text.is-failed {
          color: #DC2626;
        }
        .result-card-revert-btn {
          margin-top: 12px;
          height: 44px;
          padding: 0 20px;
          border-radius: 8px;
          background-color: #fff;
          color: #DC2626;
          border: 1px solid #DC2626;
          font-size: 16px;
        }
        .result-card-revert-btn:disabled {
          background-color: #F3F4F6;
          color: #9CA3AF;
          border-color: #D1D5DB;
          cursor: not-allowed;
        }
        .result-card-revert-confirm-btn {
          margin-top: 12px;
          height: 44px;
          padding: 0 20px;
          border-radius: 8px;
          background-color: #DC2626;
          color: #fff;
          border: none;
          font-size: 16px;
        }
        .result-card-revert-cancel-btn {
          margin-top: 12px;
          margin-left: 8px;
          height: 44px;
          padding: 0 20px;
          border-radius: 8px;
          background-color: #fff;
          color: #374151;
          border: 1px solid #D1D5DB;
          font-size: 16px;
        }
        .result-card-revert-status-text {
          color: #4B5563;
          font-size: 14px;
          margin-top: 8px;
        }
        .result-card-revert-status-text.is-failed {
          color: #DC2626;
        }
      `}</style>
      <p className="result-card-file-count" data-testid="result-file-count">
        {result.fileCount} dosya işlendi
      </p>
      {hasFolders ? (
        <ul className="result-card-folders" data-testid="result-destination-folders">
          {result.destinationFolders.map((folder) => (
            <li key={folder}>{folder}</li>
          ))}
        </ul>
      ) : (
        <p className="result-card-empty-folders" data-testid="result-no-folders">
          Hiçbir klasör oluşturulmadı.
        </p>
      )}
      <div aria-live="polite">
        <p
          className={result.status === 'failed' ? 'result-card-status-text is-failed' : 'result-card-status-text'}
          data-testid="result-status-text"
        >
          {STATUS_TEXT[result.status]}
        </p>
      </div>
      {previewState === 'loading' && (
        <p className="result-card-status-text" data-testid="result-preview-loading">
          Önizleme yükleniyor…
        </p>
      )}
      {previewState === 'error' && (
        <p className="result-card-status-text is-failed" data-testid="result-preview-error">
          Önizleme yüklenemedi.
        </p>
      )}
      {previewState === 'loaded' && preview && (
        <>
          {preview.empty ? (
            <p className="result-card-status-text" data-testid="result-preview-empty">
              Değişiklik yok
            </p>
          ) : preview.available === false ? (
            <p className="result-card-status-text" data-testid="result-preview-unavailable">
              Önizleme mevcut değil
            </p>
          ) : (
            <ul className="result-card-folders" data-testid="result-preview">
              {preview.files.map((file, index) => (
                <li key={`${file.name}-${index}`}>
                  {file.status === 'unknown' ? (
                    <span data-testid={`result-preview-unknown-${file.name}`}>{file.name || '?'} (?)</span>
                  ) : file.available === false ? (
                    <span>
                      {file.name} — Önizleme mevcut değil{file.reason ? ` (${file.reason})` : ''}
                    </span>
                  ) : (
                    <span>{file.name}</span>
                  )}
                </li>
              ))}
              {preview.truncated && (
                <li data-testid="result-preview-truncated">+{preview.total_count - preview.files.length} daha</li>
              )}
            </ul>
          )}
        </>
      )}
      {canShowRevert && revertState !== 'reverted' && revertState !== 'revert_failed' && (
        <>
          {revertState === 'confirming' ? (
            <>
              <button
                type="button"
                className="result-card-revert-confirm-btn"
                data-testid="result-revert-confirm-button"
                onClick={handleConfirmRevert}
              >
                Evet, geri al
              </button>
              <button
                type="button"
                className="result-card-revert-cancel-btn"
                data-testid="result-revert-cancel-button"
                onClick={() => setRevertState('idle')}
              >
                Vazgeç
              </button>
            </>
          ) : (
            <button
              type="button"
              className="result-card-revert-btn"
              data-testid="result-revert-button"
              disabled={revertState === 'reverting'}
              onClick={() => setRevertState('confirming')}
            >
              {revertState === 'reverting' ? 'Geri alınıyor…' : 'Geri al'}
            </button>
          )}
        </>
      )}
      {(revertState === 'reverted' || revertState === 'revert_failed' || revertState === 'error') && (
        <div aria-live="polite">
          <p
            className={
              revertState === 'reverted'
                ? 'result-card-revert-status-text'
                : 'result-card-revert-status-text is-failed'
            }
            data-testid="result-revert-status-text"
          >
            {revertState === 'reverted'
              ? 'İşlem geri alındı.'
              : revertState === 'revert_failed'
                ? 'İşlem tam olarak geri alınamadı, bazı dosyalar geri taşınamadı.'
                : 'Geri alma isteği başarısız oldu, lütfen tekrar deneyin.'}
          </p>
          {revertState === 'error' && (
            <button
              type="button"
              className="result-card-revert-btn"
              data-testid="result-revert-retry-button"
              onClick={() => setRevertState('idle')}
            >
              Tekrar dene
            </button>
          )}
        </div>
      )}
    </section>
  );
}
