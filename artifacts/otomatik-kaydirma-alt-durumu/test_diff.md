diff --git a/ui/src/components/chat/ChatScreen.test.tsx b/ui/src/components/chat/ChatScreen.test.tsx
index 6afe96f..d3293dc 100644
--- a/ui/src/components/chat/ChatScreen.test.tsx
+++ b/ui/src/components/chat/ChatScreen.test.tsx
@@ -198,4 +198,51 @@ describe('ChatScreen (dikey-mesaj-akisi / Saga #259)', () => {
     expect(screen.getByTestId('plan-approve-button')).toBeDisabled();
     expect(screen.getByTestId('plan-change-button')).toBeDisabled();
   });
+
+  function mockScrollGeometry(list: HTMLElement, { scrollTop, scrollHeight, clientHeight }: { scrollTop: number; scrollHeight: number; clientHeight: number }) {
+    Object.defineProperty(list, 'scrollTop', { value: scrollTop, writable: true, configurable: true });
+    Object.defineProperty(list, 'scrollHeight', { value: scrollHeight, configurable: true });
+    Object.defineProperty(list, 'clientHeight', { value: clientHeight, configurable: true });
+  }
+
+  it('does not show the "En yeni mesaja dön" button while the user is at the bottom (Saga #266 AC-5)', () => {
+    render(<ChatScreen />);
+
+    expect(screen.queryByTestId('chat-scroll-to-latest-button')).not.toBeInTheDocument();
+  });
+
+  it('shows the "En yeni mesaja dön" button once the user scrolls away from the bottom (Saga #266 AC-2, AC-3)', () => {
+    render(<ChatScreen />);
+    const list = screen.getByTestId('chat-message-list');
+
+    mockScrollGeometry(list, { scrollTop: 0, scrollHeight: 1000, clientHeight: 200 });
+    fireEvent.scroll(list);
+
+    expect(screen.getByTestId('chat-scroll-to-latest-button')).toBeVisible();
+  });
+
+  it('hides the button again and scrolls to bottom when "En yeni mesaja dön" is clicked (Saga #266 AC-4)', () => {
+    render(<ChatScreen />);
+    const list = screen.getByTestId('chat-message-list');
+    mockScrollGeometry(list, { scrollTop: 0, scrollHeight: 1000, clientHeight: 200 });
+    fireEvent.scroll(list);
+    expect(screen.getByTestId('chat-scroll-to-latest-button')).toBeVisible();
+
+    fireEvent.click(screen.getByTestId('chat-scroll-to-latest-button'));
+
+    expect(screen.queryByTestId('chat-scroll-to-latest-button')).not.toBeInTheDocument();
+  });
+
+  it('hides the button once the user manually scrolls back to the bottom (Saga #266 behaviour contract)', () => {
+    render(<ChatScreen />);
+    const list = screen.getByTestId('chat-message-list');
+    mockScrollGeometry(list, { scrollTop: 0, scrollHeight: 1000, clientHeight: 200 });
+    fireEvent.scroll(list);
+    expect(screen.getByTestId('chat-scroll-to-latest-button')).toBeVisible();
+
+    mockScrollGeometry(list, { scrollTop: 800, scrollHeight: 1000, clientHeight: 200 });
+    fireEvent.scroll(list);
+
+    expect(screen.queryByTestId('chat-scroll-to-latest-button')).not.toBeInTheDocument();
+  });
 });
