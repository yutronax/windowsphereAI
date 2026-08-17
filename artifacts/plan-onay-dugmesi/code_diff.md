diff --git a/ui/src/components/chat/PlanCard.tsx b/ui/src/components/chat/PlanCard.tsx
index 15dfb08..c214ee1 100644
--- a/ui/src/components/chat/PlanCard.tsx
+++ b/ui/src/components/chat/PlanCard.tsx
@@ -1,3 +1,5 @@
+import { useState } from 'react';
+
 export type PlanStep = {
   order: number;
   operationType: string;
@@ -5,15 +7,39 @@ export type PlanStep = {
   affectedFileCount: number;
 };
 
-export type Plan = { steps: PlanStep[] };
+export type Plan = {
+  steps: PlanStep[];
+  securityStatus?: 'approved' | 'rejected';
+  rejectionReason?: string;
+};
+
+type Props = { plan: Plan; onApprove?: () => void };
 
-type Props = { plan: Plan };
+const DEFAULT_REJECTION_MESSAGE = 'Bu plan güvenlik kontrolünden geçemedi.';
+const PENDING_MESSAGE = 'Güvenlik kontrolü bekleniyor…';
+const STATUS_TEXT_ID = 'plan-approve-status';
 
-export default function PlanCard({ plan }: Props) {
+export default function PlanCard({ plan, onApprove }: Props) {
+  const [hasApproved, setHasApproved] = useState(false);
   const sortedSteps = [...plan.steps]
     .map((step, index) => ({ step, index }))
     .sort((a, b) => a.step.order - b.step.order || a.index - b.index);
 
+  const isRejected = plan.securityStatus === 'rejected';
+  const isApproved = plan.securityStatus === 'approved';
+  // Fail-closed: onay düğmesi SADECE security katmanı açıkça "approved" derse
+  // etkinleşir. `securityStatus` henüz gelmemişken (undefined) veya "rejected"
+  // ise devre dışı kalır — kontrol edilmemiş bir plan asla onaylanabilir
+  // durumda gösterilmez (bağımsız red-team bulgusu, 2026-08-17).
+  const canApprove = isApproved && !hasApproved;
+  const statusText = isRejected ? plan.rejectionReason || DEFAULT_REJECTION_MESSAGE : !isApproved ? PENDING_MESSAGE : null;
+
+  function handleApprove() {
+    if (!canApprove) return;
+    setHasApproved(true);
+    onApprove?.();
+  }
+
   return (
     <section className="plan-card" data-testid="plan-card" aria-label="Önerilen plan">
       <style>{`
@@ -41,6 +67,35 @@ export default function PlanCard({ plan }: Props) {
           color: #4B5563;
           font-size: 14px;
         }
+        .plan-card-approve-btn {
+          margin-top: 12px;
+          height: 44px;
+          padding: 0 20px;
+          border-radius: 8px;
+          background-color: #2563EB;
+          color: #fff;
+          border: none;
+          font-size: 16px;
+        }
+        .plan-card-approve-btn:hover:not(:disabled) {
+          background-color: #1D4ED8;
+        }
+        .plan-card-approve-btn:focus-visible {
+          outline: 2px solid #1E40AF;
+          outline-offset: 2px;
+        }
+        .plan-card-approve-btn:disabled {
+          background-color: #94A3B8;
+          cursor: not-allowed;
+        }
+        .plan-card-status-text {
+          color: #4B5563;
+          font-size: 14px;
+          margin-top: 8px;
+        }
+        .plan-card-status-text.is-rejected {
+          color: #DC2626;
+        }
       `}</style>
       <ol className="plan-card-list">
         {sortedSteps.map(({ step, index }) => (
@@ -53,6 +108,27 @@ export default function PlanCard({ plan }: Props) {
           </li>
         ))}
       </ol>
+      <button
+        type="button"
+        className="plan-card-approve-btn"
+        data-testid="plan-approve-button"
+        disabled={!canApprove}
+        aria-describedby={statusText ? STATUS_TEXT_ID : undefined}
+        onClick={handleApprove}
+      >
+        Planı onayla
+      </button>
+      {statusText && (
+        <div aria-live="polite">
+          <p
+            id={STATUS_TEXT_ID}
+            className={isRejected ? 'plan-card-status-text is-rejected' : 'plan-card-status-text'}
+            data-testid={isRejected ? 'plan-rejection-reason' : 'plan-pending-status'}
+          >
+            {statusText}
+          </p>
+        </div>
+      )}
     </section>
   );
 }
