import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import PlanCard, { type Plan } from './PlanCard';

describe('PlanCard (plan-adimlari-kart / Saga #262)', () => {
  it('renders each step with order number, operation type, target folder and file count (AC-1, AC-2)', () => {
    const plan: Plan = {
      steps: [
        { order: 1, operationType: 'Taşı', targetFolder: 'C:/Belgeler/Arşiv', affectedFileCount: 3 },
        { order: 2, operationType: 'Sil', targetFolder: 'C:/Belgeler/Geçici', affectedFileCount: 12 },
      ],
    };
    render(<PlanCard plan={plan} />);

    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('Taşı');
    expect(items[0]).toHaveTextContent('C:/Belgeler/Arşiv');
    expect(items[0]).toHaveTextContent('3 dosya');
    expect(items[1]).toHaveTextContent('Sil');
    expect(items[1]).toHaveTextContent('12 dosya');
  });

  it('renders steps in order regardless of input array order (AC-3)', () => {
    const plan: Plan = {
      steps: [
        { order: 2, operationType: 'İkinci', targetFolder: 'B', affectedFileCount: 1 },
        { order: 1, operationType: 'Birinci', targetFolder: 'A', affectedFileCount: 1 },
      ],
    };
    render(<PlanCard plan={plan} />);

    const items = screen.getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('Birinci');
    expect(items[1]).toHaveTextContent('İkinci');
  });

  it('uses an ordered list structure for accessible step-order announcement (AC-4)', () => {
    render(<PlanCard plan={{ steps: [{ order: 1, operationType: 'Kopyala', targetFolder: 'X', affectedFileCount: 1 }] }} />);

    expect(screen.getByRole('list').tagName).toBe('OL');
  });

  it('renders an empty step list without error (behaviour contract)', () => {
    render(<PlanCard plan={{ steps: [] }} />);

    expect(screen.getByTestId('plan-card')).toBeVisible();
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
  });

  it('shows "0 dosya" instead of hiding a zero affected-file-count step (behaviour contract)', () => {
    render(<PlanCard plan={{ steps: [{ order: 1, operationType: 'Listele', targetFolder: 'X', affectedFileCount: 0 }] }} />);

    expect(screen.getByText(/0 dosya/)).toBeVisible();
  });
});
diff --git a/ui/src/components/chat/ChatScreen.test.tsx b/ui/src/components/chat/ChatScreen.test.tsx
index 197e505..0b8e1a9 100644
--- a/ui/src/components/chat/ChatScreen.test.tsx
+++ b/ui/src/components/chat/ChatScreen.test.tsx
@@ -70,6 +70,30 @@ describe('ChatScreen (dikey-mesaj-akisi / Saga #259)', () => {
     expect(screen.getByTestId('chat-message-list').children).toHaveLength(0);
   });
 
+  it('renders a PlanCard alongside an assistant message that carries a plan (Saga #262 integration)', () => {
+    render(
+      <ChatScreen
+        initialMessages={[
+          {
+            id: 'p1',
+            role: 'assistant',
+            text: 'Önerilen plan:',
+            plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }] },
+          },
+        ]}
+      />,
+    );
+
+    expect(screen.getByTestId('plan-card')).toBeVisible();
+    expect(screen.getByText('Taşı')).toBeVisible();
+  });
+
+  it('does not render a PlanCard when a message has no plan (Saga #262 integration)', () => {
+    render(<ChatScreen initialMessages={[{ id: 'm1', role: 'assistant', text: 'sade metin' }]} />);
+
+    expect(screen.queryByTestId('plan-card')).not.toBeInTheDocument();
+  });
+
   it('keeps multiple sent messages selectable and in sequential order (AC-1)', () => {
     render(<ChatScreen />);
     const textarea = screen.getByTestId('chat-input-textarea');
