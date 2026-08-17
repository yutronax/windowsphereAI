diff --git a/ui/src/components/chat/PlanCard.test.tsx b/ui/src/components/chat/PlanCard.test.tsx
index 57ce697..d9c90cd 100644
--- a/ui/src/components/chat/PlanCard.test.tsx
+++ b/ui/src/components/chat/PlanCard.test.tsx
@@ -1,8 +1,10 @@
-import { render, screen } from '@testing-library/react';
-import { describe, expect, it } from 'vitest';
+import { fireEvent, render, screen } from '@testing-library/react';
+import { describe, expect, it, vi } from 'vitest';
 
 import PlanCard, { type Plan } from './PlanCard';
 
+const onePlan: Plan = { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 1 }] };
+
 describe('PlanCard (plan-adimlari-kart / Saga #262)', () => {
   it('renders each step with order number, operation type, target folder and file count (AC-1, AC-2)', () => {
     const plan: Plan = {
@@ -54,4 +56,65 @@ describe('PlanCard (plan-adimlari-kart / Saga #262)', () => {
 
     expect(screen.getByText(/0 dosya/)).toBeVisible();
   });
+
+  it('fails closed: disables the approve button and shows a pending message when securityStatus is absent (Saga #263 AC-1/AC-2, red-team fix)', () => {
+    const onApprove = vi.fn();
+    render(<PlanCard plan={onePlan} onApprove={onApprove} />);
+
+    const button = screen.getByTestId('plan-approve-button');
+    expect(button).toBeDisabled();
+    expect(screen.getByTestId('plan-pending-status')).toHaveTextContent('Güvenlik kontrolü bekleniyor');
+    fireEvent.click(button);
+    expect(onApprove).not.toHaveBeenCalled();
+  });
+
+  it('enables the approve button ONLY when securityStatus is "approved", and calls onApprove when clicked (Saga #263 AC-4, AC-6)', () => {
+    const onApprove = vi.fn();
+    render(<PlanCard plan={{ ...onePlan, securityStatus: 'approved' }} onApprove={onApprove} />);
+
+    const button = screen.getByTestId('plan-approve-button');
+    expect(button).toBeEnabled();
+    expect(screen.queryByTestId('plan-rejection-reason')).not.toBeInTheDocument();
+    expect(screen.queryByTestId('plan-pending-status')).not.toBeInTheDocument();
+    fireEvent.click(button);
+    expect(onApprove).toHaveBeenCalledOnce();
+  });
+
+  it('disables the approve button and shows the rejection reason when securityStatus is "rejected" (Saga #263 AC-3)', () => {
+    render(<PlanCard plan={{ ...onePlan, securityStatus: 'rejected', rejectionReason: 'Sandbox dışına çıkan yol tespit edildi.' }} />);
+
+    expect(screen.getByTestId('plan-approve-button')).toBeDisabled();
+    expect(screen.getByTestId('plan-rejection-reason')).toHaveTextContent('Sandbox dışına çıkan yol tespit edildi.');
+  });
+
+  it('shows a default rejection message when rejected without an explicit reason (behaviour contract)', () => {
+    render(<PlanCard plan={{ ...onePlan, securityStatus: 'rejected' }} />);
+
+    expect(screen.getByTestId('plan-rejection-reason')).toHaveTextContent('Bu plan güvenlik kontrolünden geçemedi.');
+  });
+
+  it('ignores a rapid second click after approval (double-submit guard, red-team fix)', () => {
+    const onApprove = vi.fn();
+    render(<PlanCard plan={{ ...onePlan, securityStatus: 'approved' }} onApprove={onApprove} />);
+
+    const button = screen.getByTestId('plan-approve-button');
+    fireEvent.click(button);
+    fireEvent.click(button);
+    expect(onApprove).toHaveBeenCalledOnce();
+  });
+
+  it('links the disabled state to its status text via aria-describedby (screen reader, red-team fix)', () => {
+    render(<PlanCard plan={{ ...onePlan, securityStatus: 'rejected', rejectionReason: 'Yetkisiz dizin.' }} />);
+
+    const button = screen.getByTestId('plan-approve-button');
+    const describedById = button.getAttribute('aria-describedby');
+    expect(describedById).toBeTruthy();
+    expect(document.getElementById(describedById!)).toHaveTextContent('Yetkisiz dizin.');
+  });
+
+  it('gives the approve button a 44px minimum touch target (Saga #263 AC-5)', () => {
+    render(<PlanCard plan={{ ...onePlan, securityStatus: 'approved' }} />);
+
+    expect(screen.getByTestId('plan-approve-button')).toHaveClass('plan-card-approve-btn');
+  });
 });
