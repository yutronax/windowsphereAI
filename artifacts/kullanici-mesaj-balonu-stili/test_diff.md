diff --git a/ui/src/components/chat/ChatScreen.test.tsx b/ui/src/components/chat/ChatScreen.test.tsx
index 32ea091..ed75fed 100644
--- a/ui/src/components/chat/ChatScreen.test.tsx
+++ b/ui/src/components/chat/ChatScreen.test.tsx
@@ -286,4 +286,35 @@ describe('ChatScreen (dikey-mesaj-akisi / Saga #259)', () => {
     expect(screen.getByTestId('plan-loading-indicator')).toBeVisible();
     expect(screen.queryByTestId('plan-error-indicator')).not.toBeInTheDocument();
   });
+
+  it('wraps a user message in a right-aligned blue chat-message-bubble (Saga #260 AC-1, AC-2, AC-3)', () => {
+    render(<ChatScreen initialMessages={[{ id: 'u1', role: 'user', text: 'merhaba dünya' }]} />);
+
+    const item = screen.getByTestId('chat-message-u1');
+    expect(item).toHaveAttribute('data-role', 'user');
+    const bubble = screen.getByTestId('chat-message-bubble-u1');
+    expect(bubble).toHaveClass('chat-message-bubble');
+    expect(bubble).toHaveTextContent('merhaba dünya');
+  });
+
+  it('keeps assistant messages structurally sharing chat-message-bubble without the user-specific role styling target (Saga #260 AC-5)', () => {
+    render(<ChatScreen initialMessages={[{ id: 'a1', role: 'assistant', text: 'yanıt metni' }]} />);
+
+    const item = screen.getByTestId('chat-message-a1');
+    expect(item).toHaveAttribute('data-role', 'assistant');
+    expect(screen.getByTestId('chat-message-bubble-a1')).toHaveClass('chat-message-bubble');
+  });
+
+  it('renders PlanCard outside the message bubble, after it (Saga #260 AC-6, regression)', () => {
+    render(
+      <ChatScreen
+        initialMessages={[
+          { id: 'p1', role: 'assistant', text: 'Önerilen plan:', plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 1 }] } },
+        ]}
+      />,
+    );
+
+    const bubble = screen.getByTestId('chat-message-bubble-p1');
+    expect(bubble).not.toContainElement(screen.getByTestId('plan-card'));
+  });
 });
