diff --git a/ui/src/components/chat/ChatScreen.test.tsx b/ui/src/components/chat/ChatScreen.test.tsx
index 0b8e1a9..654b093 100644
--- a/ui/src/components/chat/ChatScreen.test.tsx
+++ b/ui/src/components/chat/ChatScreen.test.tsx
@@ -108,4 +108,59 @@ describe('ChatScreen (dikey-mesaj-akisi / Saga #259)', () => {
     expect(items[0]).toHaveTextContent('birinci');
     expect(items[1]).toHaveTextContent('ikinci');
   });
+
+  it('focuses the textarea and shows an editing hint when "Planı değiştir" is clicked, without approving (Saga #264 AC-1, AC-2, AC-3)', () => {
+    render(
+      <ChatScreen
+        initialMessages={[
+          { id: 'p1', role: 'assistant', text: 'Önerilen plan:', plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'approved' } },
+        ]}
+      />,
+    );
+
+    expect(screen.queryByTestId('chat-edit-plan-hint')).not.toBeInTheDocument();
+    fireEvent.click(screen.getByTestId('plan-change-button'));
+
+    expect(screen.getByTestId('chat-edit-plan-hint')).toBeVisible();
+    expect(screen.getByTestId('chat-input-textarea')).toHaveFocus();
+    expect(screen.getByTestId('plan-approve-button')).toBeEnabled();
+  });
+
+  it('marks the edited plan as stale and clears the hint once the new message is sent (Saga #264 AC-4, AC-5)', () => {
+    const onSendMessage = vi.fn();
+    render(
+      <ChatScreen
+        onSendMessage={onSendMessage}
+        initialMessages={[
+          { id: 'p1', role: 'assistant', text: 'Önerilen plan:', plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'approved' } },
+        ]}
+      />,
+    );
+
+    fireEvent.click(screen.getByTestId('plan-change-button'));
+    const textarea = screen.getByTestId('chat-input-textarea');
+    fireEvent.change(textarea, { target: { value: 'başka bir klasöre taşı' } });
+    fireEvent.click(screen.getByText('Gönder'));
+
+    expect(screen.queryByTestId('chat-edit-plan-hint')).not.toBeInTheDocument();
+    expect(screen.getByTestId('plan-stale-status')).toHaveTextContent('Bu plan artık geçerli değil, yeni plan bekleniyor.');
+    expect(screen.getByTestId('plan-approve-button')).toBeDisabled();
+    expect(onSendMessage).toHaveBeenCalledWith(expect.objectContaining({ text: 'başka bir klasöre taşı' }));
+  });
+
+  it('does not mark a plan stale when the user sends an empty message while editing (behaviour contract)', () => {
+    render(
+      <ChatScreen
+        initialMessages={[
+          { id: 'p1', role: 'assistant', text: 'Önerilen plan:', plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'approved' } },
+        ]}
+      />,
+    );
+
+    fireEvent.click(screen.getByTestId('plan-change-button'));
+    fireEvent.keyDown(screen.getByTestId('chat-input-textarea'), { key: 'Enter' });
+
+    expect(screen.getByTestId('chat-edit-plan-hint')).toBeVisible();
+    expect(screen.getByTestId('plan-approve-button')).toBeEnabled();
+  });
 });
diff --git a/ui/src/components/chat/PlanCard.test.tsx b/ui/src/components/chat/PlanCard.test.tsx
index d9c90cd..9ccfeb4 100644
--- a/ui/src/components/chat/PlanCard.test.tsx
+++ b/ui/src/components/chat/PlanCard.test.tsx
@@ -117,4 +117,26 @@ describe('PlanCard (plan-adimlari-kart / Saga #262)', () => {
 
     expect(screen.getByTestId('plan-approve-button')).toHaveClass('plan-card-approve-btn');
   });
+
+  it('calls onChangePlan and NOT onApprove when "Planı değiştir" is clicked (Saga #264 AC-1)', () => {
+    const onApprove = vi.fn();
+    const onChangePlan = vi.fn();
+    render(<PlanCard plan={{ ...onePlan, securityStatus: 'approved' }} onApprove={onApprove} onChangePlan={onChangePlan} />);
+
+    fireEvent.click(screen.getByTestId('plan-change-button'));
+
+    expect(onChangePlan).toHaveBeenCalledOnce();
+    expect(onApprove).not.toHaveBeenCalled();
+  });
+
+  it('permanently disables approval and shows a stale message when stale=true (Saga #264 AC-4)', () => {
+    const onApprove = vi.fn();
+    render(<PlanCard plan={{ ...onePlan, securityStatus: 'approved' }} onApprove={onApprove} stale />);
+
+    const button = screen.getByTestId('plan-approve-button');
+    expect(button).toBeDisabled();
+    expect(screen.getByTestId('plan-stale-status')).toHaveTextContent('Bu plan artık geçerli değil, yeni plan bekleniyor.');
+    fireEvent.click(button);
+    expect(onApprove).not.toHaveBeenCalled();
+  });
 });
