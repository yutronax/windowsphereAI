diff --git a/ui/src/components/chat/ChatScreen.test.tsx b/ui/src/components/chat/ChatScreen.test.tsx
index ed75fed..baec9e2 100644
--- a/ui/src/components/chat/ChatScreen.test.tsx
+++ b/ui/src/components/chat/ChatScreen.test.tsx
@@ -305,6 +305,22 @@ describe('ChatScreen (dikey-mesaj-akisi / Saga #259)', () => {
     expect(screen.getByTestId('chat-message-bubble-a1')).toHaveClass('chat-message-bubble');
   });
 
+  it('keeps the user bubble left unaffected while the assistant bubble gets the neutral surface (Saga #261 AC-1, AC-2)', () => {
+    render(
+      <ChatScreen
+        initialMessages={[
+          { id: 'u1', role: 'user', text: 'kullanıcı mesajı' },
+          { id: 'a1', role: 'assistant', text: 'asistan mesajı' },
+        ]}
+      />,
+    );
+
+    expect(screen.getByTestId('chat-message-u1')).toHaveAttribute('data-role', 'user');
+    expect(screen.getByTestId('chat-message-a1')).toHaveAttribute('data-role', 'assistant');
+    expect(screen.getByTestId('chat-message-bubble-u1')).toHaveClass('chat-message-bubble');
+    expect(screen.getByTestId('chat-message-bubble-a1')).toHaveClass('chat-message-bubble');
+  });
+
   it('renders PlanCard outside the message bubble, after it (Saga #260 AC-6, regression)', () => {
     render(
       <ChatScreen
