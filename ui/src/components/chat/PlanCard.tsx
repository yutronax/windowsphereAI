import { useState } from 'react';
import Button from '../primitives/Button';
import Card from '../primitives/Card';
import { tokens } from '../../tokens';

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
// Saga #311: "yanlış klasör, 1000 dosya" riskine karşı — bu eşiği aşan
// planlar tek tıkla değil, ikinci bir açık onay adımıyla onaylanabilir.
const BULK_CONFIRM_THRESHOLD = 20;

export default function PlanCard({ plan, onApprove, onChangePlan, stale = false, isGeneratingPlan = false }: Props) {
  const [hasApproved, setHasApproved] = useState(false);
  const [isConfirmingBulk, setIsConfirmingBulk] = useState(false);
  const sortedSteps = [...plan.steps]
    .map((step, index) => ({ step, index }))
    .sort((a, b) => a.step.order - b.step.order || a.index - b.index);
  const totalAffectedFileCount = plan.steps.reduce((sum, step) => sum + step.affectedFileCount, 0);
  const isBulk = totalAffectedFileCount > BULK_CONFIRM_THRESHOLD;

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
    if (isBulk && !isConfirmingBulk) {
      setIsConfirmingBulk(true);
      return;
    }
    setHasApproved(true);
    onApprove?.();
  }

  function handleCancelBulkConfirm() {
    setIsConfirmingBulk(false);
  }

  return (
    <Card
      data-testid="plan-card"
      aria-label="Önerilen plan"
      className="plan-card"
    >
      <style>{`
        .plan-card {
          padding: 12px 16px;
          margin-top: 8px;
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
          color: ${tokens.colors.textSecondary};
          font-size: ${tokens.fontSize.small};
        }
        .plan-card-approve-btn {
          margin-top: 12px;
        }
        .plan-card-status-text {
          color: ${tokens.colors.textSecondary};
          font-size: ${tokens.fontSize.small};
          margin-top: 8px;
        }
        .plan-card-status-text.is-rejected {
          color: ${tokens.colors.danger};
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
      {isConfirmingBulk ? (
        <>
          <Button
            variant="primary"
            className="plan-card-approve-btn"
            data-testid="plan-bulk-confirm-button"
            onClick={handleApprove}
          >
            Evet, onayla ({totalAffectedFileCount} dosya)
          </Button>
          <Button
            variant="secondary"
            style={{ marginTop: '12px', marginLeft: '8px' }}
            data-testid="plan-bulk-confirm-cancel-button"
            onClick={handleCancelBulkConfirm}
          >
            Vazgeç
          </Button>
        </>
      ) : (
        <>
          <Button
            variant="primary"
            className="plan-card-approve-btn"
            data-testid="plan-approve-button"
            disabled={!canApprove}
            aria-describedby={statusText ? STATUS_TEXT_ID : undefined}
            onClick={handleApprove}
          >
            Planı onayla
          </Button>
          <Button
            variant="secondary"
            style={{ marginTop: '12px', marginLeft: '8px' }}
            data-testid="plan-change-button"
            disabled={isGeneratingPlan}
            onClick={() => onChangePlan?.()}
          >
            Planı değiştir
          </Button>
        </>
      )}
      {isBulk && isConfirmingBulk && (
        <div aria-live="polite">
          <p className="plan-card-status-text" data-testid="plan-bulk-confirm-warning">
            Bu işlem {totalAffectedFileCount} dosyayı etkileyecek — devam etmeden önce hedef klasörleri kontrol edin.
          </p>
        </div>
      )}
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
    </Card>
  );
}
