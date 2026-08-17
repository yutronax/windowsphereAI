diff --git a/ui/src/components/chat/ChatScreen.test.tsx b/ui/src/components/chat/ChatScreen.test.tsx
index d3293dc..32ea091 100644
--- a/ui/src/components/chat/ChatScreen.test.tsx
+++ b/ui/src/components/chat/ChatScreen.test.tsx
@@ -245,4 +245,45 @@ describe('ChatScreen (dikey-mesaj-akisi / Saga #259)', () => {
 
     expect(screen.queryByTestId('chat-scroll-to-latest-button')).not.toBeInTheDocument();
   });
+
+  it('shows the error indicator with a "Tekrar dene" button when planError is set (Saga #267 AC-1)', () => {
+    render(<ChatScreen planError="Yerel API'ye ulaşılamadı." />);
+
+    const indicator = screen.getByTestId('plan-error-indicator');
+    expect(indicator).toHaveTextContent("Yerel API'ye ulaşılamadı.");
+    expect(indicator).toHaveAttribute('role', 'alert');
+    expect(screen.getByTestId('plan-retry-button')).toBeVisible();
+  });
+
+  it('calls onRetry when "Tekrar dene" is clicked, without any auto-dismiss (Saga #267 AC-2, AC-3)', () => {
+    const onRetry = vi.fn();
+    render(<ChatScreen planError="Plan üretilemedi." onRetry={onRetry} />);
+
+    fireEvent.click(screen.getByTestId('plan-retry-button'));
+
+    expect(onRetry).toHaveBeenCalledOnce();
+    expect(screen.getByTestId('plan-error-indicator')).toBeVisible();
+  });
+
+  it('does not show the error indicator when planError is null/omitted (regression)', () => {
+    render(<ChatScreen />);
+
+    expect(screen.queryByTestId('plan-error-indicator')).not.toBeInTheDocument();
+  });
+
+  it('keeps the textarea and send button enabled while an error is shown (Saga #267 AC-5)', () => {
+    render(<ChatScreen planError="Hata oluştu." />);
+
+    const textarea = screen.getByTestId('chat-input-textarea');
+    expect(textarea).toBeEnabled();
+    fireEvent.change(textarea, { target: { value: 'yeniden deneme mesajı' } });
+    expect(screen.getByText('Gönder')).toBeEnabled();
+  });
+
+  it('suppresses the error indicator in favour of the loading indicator when both are set (Saga #267 behaviour contract)', () => {
+    render(<ChatScreen planError="Eski hata." isGeneratingPlan />);
+
+    expect(screen.getByTestId('plan-loading-indicator')).toBeVisible();
+    expect(screen.queryByTestId('plan-error-indicator')).not.toBeInTheDocument();
+  });
 });
