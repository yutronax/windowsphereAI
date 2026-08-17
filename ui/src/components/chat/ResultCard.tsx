export type TransactionResult = {
  fileCount: number;
  destinationFolders: string[];
  status: 'completed' | 'partial' | 'failed';
};

type Props = {
  result: TransactionResult;
};

const STATUS_TEXT: Record<TransactionResult['status'], string> = {
  completed: 'İşlem tamamlandı.',
  partial: 'İşlem kısmen tamamlandı.',
  failed: 'İşlem tamamlanamadı.',
};

export default function ResultCard({ result }: Props) {
  const hasFolders = result.destinationFolders.length > 0;

  return (
    <section className="result-card" data-testid="result-card" aria-label="İşlem sonucu">
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
    </section>
  );
}
