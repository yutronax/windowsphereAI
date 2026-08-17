diff --git a/ui/src/components/chat/ChatScreen.test.tsx b/ui/src/components/chat/ChatScreen.test.tsx
index 654b093..6afe96f 100644
--- a/ui/src/components/chat/ChatScreen.test.tsx
+++ b/ui/src/components/chat/ChatScreen.test.tsx
@@ -163,4 +163,39 @@ describe('ChatScreen (dikey-mesaj-akisi / Saga #259)', () => {
     expect(screen.getByTestId('chat-edit-plan-hint')).toBeVisible();
     expect(screen.getByTestId('plan-approve-button')).toBeEnabled();
   });
+
+  it('shows the "Plan hazırlanıyor…" indicator and disables input/send while isGeneratingPlan (Saga #265 AC-1, AC-3)', () => {
+    render(<ChatScreen isGeneratingPlan />);
+
+    expect(screen.getByTestId('plan-loading-indicator')).toHaveTextContent('Plan hazırlanıyor…');
+    expect(screen.getByTestId('chat-input-textarea')).toBeDisabled();
+    expect(screen.getByText('Gönder')).toBeDisabled();
+  });
+
+  it('does not show the loading indicator and keeps the input usable when isGeneratingPlan is false/omitted (Saga #265 AC-4, regression)', () => {
+    render(<ChatScreen />);
+
+    expect(screen.queryByTestId('plan-loading-indicator')).not.toBeInTheDocument();
+    expect(screen.getByTestId('chat-input-textarea')).toBeEnabled();
+  });
+
+  it('announces the loading indicator in an aria-live polite region (Saga #265 AC-5)', () => {
+    render(<ChatScreen isGeneratingPlan />);
+
+    expect(screen.getByTestId('plan-loading-indicator')).toHaveAttribute('aria-live', 'polite');
+  });
+
+  it('disables a visible plan card\'s approve/change-plan buttons while isGeneratingPlan, avoiding contradictory UI (Saga #265 red-team fix)', () => {
+    render(
+      <ChatScreen
+        isGeneratingPlan
+        initialMessages={[
+          { id: 'p1', role: 'assistant', text: 'Önerilen plan:', plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'approved' } },
+        ]}
+      />,
+    );
+
+    expect(screen.getByTestId('plan-approve-button')).toBeDisabled();
+    expect(screen.getByTestId('plan-change-button')).toBeDisabled();
+  });
 });
diff --git a/ui/src/components/chat/PlanCard.test.tsx b/ui/src/components/chat/PlanCard.test.tsx
index 9ccfeb4..d078927 100644
--- a/ui/src/components/chat/PlanCard.test.tsx
+++ b/ui/src/components/chat/PlanCard.test.tsx
@@ -129,6 +129,22 @@ describe('PlanCard (plan-adimlari-kart / Saga #262)', () => {
     expect(onApprove).not.toHaveBeenCalled();
   });
 
+  it('disables both approve and change-plan buttons while a new plan is generating (Saga #265 red-team fix)', () => {
+    const onApprove = vi.fn();
+    const onChangePlan = vi.fn();
+    render(
+      <PlanCard
+        plan={{ ...onePlan, securityStatus: 'approved' }}
+        onApprove={onApprove}
+        onChangePlan={onChangePlan}
+        isGeneratingPlan
+      />,
+    );
+
+    expect(screen.getByTestId('plan-approve-button')).toBeDisabled();
+    expect(screen.getByTestId('plan-change-button')).toBeDisabled();
+  });
+
   it('permanently disables approval and shows a stale message when stale=true (Saga #264 AC-4)', () => {
     const onApprove = vi.fn();
     render(<PlanCard plan={{ ...onePlan, securityStatus: 'approved' }} onApprove={onApprove} stale />);
