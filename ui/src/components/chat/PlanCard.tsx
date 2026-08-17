import { useState } from 'react';

// Saga #281: backend'in üretebileceği bilinen operasyon türleri
// (backend/models.py: OperationType enum ile birebir eşleşir).
// `planValidation.ts` bu listeyi buradan import eder — `PlanStep`in
// sahibi burası, tip döngüsüne (circular import) girmemek için.
export const KNOWN_OPERATION_TYPES = ['Taşı', 'Kopyala', 'Sil', 'Yeniden Adlandır', 'Listele'] as const;

export type PlanStep = {
  order: number;
  operationType: (typeof KNOWN_OPERATION_TYPES)[number];
  targetFolder: string;
  affectedFileCount: number;
};

export type Plan = {
  steps: PlanStep[];
  securityStatus?: 'approved' | 'rejected';
  rejectionReason?: string;
};

type Props = {
  plan: Plan;
  onApprove?: () => void;
  onChangePlan?: () => void;
  stale?: boolean;
  isGeneratingPlan?: boolean;
};

const DEFAULT_REJECTION_MESSAGE = 'Bu plan güvenlik kontrolünden geçemedi.';
const PENDING_MESSAGE = 'Güvenlik kontrolü bekleniyor…';
const STALE_MESSAGE = 'Bu plan artık geçerli değil, yeni plan bekleniyor.';
const STATUS_TEXT_ID = 'plan-approve-status';

export default function PlanCard({ plan, onApprove, onChangePlan, stale = false, isGeneratingPlan = false }: Props) {
  const [hasApproved, setHasApproved] = useState(false);
  const sortedSteps = [...plan.steps]
    .map((step, index) => ({ step, index }))
    .sort((a, b) => a.step.order - b.step.order || a.index - b.index);

  const isRejected = plan.securityStatus === 'rejected';
  const isApproved = plan.securityStatus === 'approved';
  // Fail-closed: onay düğmesi SADECE security katmanı açıkça "approved" derse
  // etkinleşir. `securityStatus` henüz gelmemişken (undefined) veya "rejected"
  // ise devre dışı kalır — kontrol edilmemiş bir plan asla onaylanabilir
  // durumda gösterilmez (bağımsız red-team bulgusu, 2026-08-17).
  // Yeni bir plan üretilirken (isGeneratingPlan) bu plan üzerinde onay/değiştir
  // eylemi de kilitlenir — aksi halde "Plan hazırlanıyor…" ile "Planı değiştirmek
  // için yazın" ipucu aynı anda çelişkili biçimde görünebilir (red-team bulgusu,
  // Saga #265).
  const canApprove = isApproved && !hasApproved && !stale && !isGeneratingPlan;
  const statusText = stale
    ? STALE_MESSAGE
    : isRejected
      ? plan.rejectionReason || DEFAULT_REJECTION_MESSAGE
      : !isApproved
        ? PENDING_MESSAGE
        : null;

  function handleApprove() {
    if (!canApprove) return;
    setHasApproved(true);
    onApprove?.();
  }

  return (
    <section className="plan-card" data-testid="plan-card" aria-label="Önerilen plan">
      <style>{`
        .plan-card {
          border: 1px solid #E5E7EB;
          border-radius: 12px;
          padding: 12px 16px;
          margin-top: 8px;
          background-color: #FAFAFA;
        }
        .plan-card-list {
          margin: 0;
          padding-left: 20px;
        }
        .plan-card-step {
          margin-bottom: 8px;
        }
        .plan-card-step:last-child {
          margin-bottom: 0;
        }
        .plan-card-operation {
          font-weight: 600;
        }
        .plan-card-meta {
          color: #4B5563;
          font-size: 14px;
        }
        .plan-card-approve-btn {
          margin-top: 12px;
          height: 44px;
          padding: 0 20px;
          border-radius: 8px;
          background-color: #2563EB;
          color: #fff;
          border: none;
          font-size: 16px;
        }
        .plan-card-approve-btn:hover:not(:disabled) {
          background-color: #1D4ED8;
        }
        .plan-card-approve-btn:focus-visible {
          outline: 2px solid #1E40AF;
          outline-offset: 2px;
        }
        .plan-card-approve-btn:disabled {
          background-color: #94A3B8;
          cursor: not-allowed;
        }
        .plan-card-status-text {
          color: #4B5563;
          font-size: 14px;
          margin-top: 8px;
        }
        .plan-card-status-text.is-rejected {
          color: #DC2626;
        }
        .plan-card-change-btn {
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
      `}</style>
      <ol className="plan-card-list">
        {sortedSteps.map(({ step, index }) => (
          <li key={`${step.order}-${index}`} className="plan-card-step" data-testid={`plan-step-${step.order}-${index}`}>
            <span className="plan-card-operation">{step.operationType}</span>
            {' — '}
            <span className="plan-card-meta">
              {step.targetFolder} ({step.affectedFileCount} dosya)
            </span>
          </li>
        ))}
      </ol>
      <button
        type="button"
        className="plan-card-approve-btn"
        data-testid="plan-approve-button"
        disabled={!canApprove}
        aria-describedby={statusText ? STATUS_TEXT_ID : undefined}
        onClick={handleApprove}
      >
        Planı onayla
      </button>
      <button
        type="button"
        className="plan-card-change-btn"
        data-testid="plan-change-button"
        disabled={isGeneratingPlan}
        onClick={() => onChangePlan?.()}
      >
        Planı değiştir
      </button>
      {statusText && (
        <div aria-live="polite">
          <p
            id={STATUS_TEXT_ID}
            className={isRejected && !stale ? 'plan-card-status-text is-rejected' : 'plan-card-status-text'}
            data-testid={stale ? 'plan-stale-status' : isRejected ? 'plan-rejection-reason' : 'plan-pending-status'}
          >
            {statusText}
          </p>
        </div>
      )}
    </section>
  );
}
