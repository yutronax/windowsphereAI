import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import ChatScreen from './ChatScreen';

describe('ChatScreen (dikey-mesaj-akisi / Saga #259)', () => {
  it('renders no messages initially when none are provided (AC-1)', () => {
    render(<ChatScreen />);

    expect(screen.getByTestId('chat-message-list').children).toHaveLength(0);
  });

  it('renders provided messages in order inside the scrollable list region (AC-1)', () => {
    render(
      <ChatScreen
        initialMessages={[
          { id: 'a', role: 'user', text: 'ilk mesaj' },
          { id: 'b', role: 'assistant', text: 'ikinci mesaj' },
        ]}
      />,
    );

    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('ilk mesaj');
    expect(items[1]).toHaveTextContent('ikinci mesaj');
  });

  it('exposes the message list as an accessible polite live region (AC-1, screen reader)', () => {
    render(<ChatScreen />);

    const list = screen.getByTestId('chat-message-list');
    expect(list).toHaveAttribute('role', 'log');
    expect(list).toHaveAttribute('aria-live', 'polite');
  });

  it('appends a new message and clears the draft when the send button is clicked (AC-1)', () => {
    const onSendMessage = vi.fn();
    render(<ChatScreen onSendMessage={onSendMessage} />);

    const textarea = screen.getByTestId('chat-input-textarea');
    fireEvent.change(textarea, { target: { value: 'merhaba' } });
    fireEvent.click(screen.getByText('Gönder'));

    expect(screen.getByText('merhaba')).toBeVisible();
    expect(textarea).toHaveValue('');
    expect(onSendMessage).toHaveBeenCalledWith(expect.objectContaining({ text: 'merhaba', role: 'user' }));
  });

  it('sends the message on Enter without Shift, and does not send on empty/whitespace text (AC-1)', () => {
    render(<ChatScreen />);

    const textarea = screen.getByTestId('chat-input-textarea');
    fireEvent.change(textarea, { target: { value: '   ' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(screen.getByTestId('chat-message-list').children).toHaveLength(0);

    fireEvent.change(textarea, { target: { value: 'enter ile gönder' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(screen.getByText('enter ile gönder')).toBeVisible();
  });

  it('keeps newline insertion on Shift+Enter instead of sending (AC-1)', () => {
    render(<ChatScreen />);

    const textarea = screen.getByTestId('chat-input-textarea');
    fireEvent.change(textarea, { target: { value: 'satır' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });

    expect(screen.getByTestId('chat-message-list').children).toHaveLength(0);
  });

  it('renders a PlanCard alongside an assistant message that carries a plan (Saga #262 integration)', () => {
    render(
      <ChatScreen
        initialMessages={[
          {
            id: 'p1',
            role: 'assistant',
            text: 'Önerilen plan:',
            plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }] },
          },
        ]}
      />,
    );

    expect(screen.getByTestId('plan-card')).toBeVisible();
    expect(screen.getByText('Taşı')).toBeVisible();
  });

  it('does not render a PlanCard when a message has no plan (Saga #262 integration)', () => {
    render(<ChatScreen initialMessages={[{ id: 'm1', role: 'assistant', text: 'sade metin' }]} />);

    expect(screen.queryByTestId('plan-card')).not.toBeInTheDocument();
  });

  it('keeps multiple sent messages selectable and in sequential order (AC-1)', () => {
    render(<ChatScreen />);
    const textarea = screen.getByTestId('chat-input-textarea');

    fireEvent.change(textarea, { target: { value: 'birinci' } });
    fireEvent.click(screen.getByText('Gönder'));
    fireEvent.change(textarea, { target: { value: 'ikinci' } });
    fireEvent.click(screen.getByText('Gönder'));

    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('birinci');
    expect(items[1]).toHaveTextContent('ikinci');
  });

  it('focuses the textarea and shows an editing hint when "Planı değiştir" is clicked, without approving (Saga #264 AC-1, AC-2, AC-3)', () => {
    render(
      <ChatScreen
        initialMessages={[
          { id: 'p1', role: 'assistant', text: 'Önerilen plan:', plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'approved' } },
        ]}
      />,
    );

    expect(screen.queryByTestId('chat-edit-plan-hint')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('plan-change-button'));

    expect(screen.getByTestId('chat-edit-plan-hint')).toBeVisible();
    expect(screen.getByTestId('chat-input-textarea')).toHaveFocus();
    expect(screen.getByTestId('plan-approve-button')).toBeEnabled();
  });

  it('marks the edited plan as stale and clears the hint once the new message is sent (Saga #264 AC-4, AC-5)', () => {
    const onSendMessage = vi.fn();
    render(
      <ChatScreen
        onSendMessage={onSendMessage}
        initialMessages={[
          { id: 'p1', role: 'assistant', text: 'Önerilen plan:', plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'approved' } },
        ]}
      />,
    );

    fireEvent.click(screen.getByTestId('plan-change-button'));
    const textarea = screen.getByTestId('chat-input-textarea');
    fireEvent.change(textarea, { target: { value: 'başka bir klasöre taşı' } });
    fireEvent.click(screen.getByText('Gönder'));

    expect(screen.queryByTestId('chat-edit-plan-hint')).not.toBeInTheDocument();
    expect(screen.getByTestId('plan-stale-status')).toHaveTextContent('Bu plan artık geçerli değil, yeni plan bekleniyor.');
    expect(screen.getByTestId('plan-approve-button')).toBeDisabled();
    expect(onSendMessage).toHaveBeenCalledWith(expect.objectContaining({ text: 'başka bir klasöre taşı' }));
  });

  it('does not mark a plan stale when the user sends an empty message while editing (behaviour contract)', () => {
    render(
      <ChatScreen
        initialMessages={[
          { id: 'p1', role: 'assistant', text: 'Önerilen plan:', plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'approved' } },
        ]}
      />,
    );

    fireEvent.click(screen.getByTestId('plan-change-button'));
    fireEvent.keyDown(screen.getByTestId('chat-input-textarea'), { key: 'Enter' });

    expect(screen.getByTestId('chat-edit-plan-hint')).toBeVisible();
    expect(screen.getByTestId('plan-approve-button')).toBeEnabled();
  });

  it('shows the "Plan hazırlanıyor…" indicator and disables input/send while isGeneratingPlan (Saga #265 AC-1, AC-3)', () => {
    render(<ChatScreen isGeneratingPlan />);

    expect(screen.getByTestId('plan-loading-indicator')).toHaveTextContent('Plan hazırlanıyor…');
    expect(screen.getByTestId('chat-input-textarea')).toBeDisabled();
    expect(screen.getByText('Gönder')).toBeDisabled();
  });

  it('does not show the loading indicator and keeps the input usable when isGeneratingPlan is false/omitted (Saga #265 AC-4, regression)', () => {
    render(<ChatScreen />);

    expect(screen.queryByTestId('plan-loading-indicator')).not.toBeInTheDocument();
    expect(screen.getByTestId('chat-input-textarea')).toBeEnabled();
  });

  it('announces the loading indicator in an aria-live polite region (Saga #265 AC-5)', () => {
    render(<ChatScreen isGeneratingPlan />);

    expect(screen.getByTestId('plan-loading-indicator')).toHaveAttribute('aria-live', 'polite');
  });

  it('disables a visible plan card\'s approve/change-plan buttons while isGeneratingPlan, avoiding contradictory UI (Saga #265 red-team fix)', () => {
    render(
      <ChatScreen
        isGeneratingPlan
        initialMessages={[
          { id: 'p1', role: 'assistant', text: 'Önerilen plan:', plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'approved' } },
        ]}
      />,
    );

    expect(screen.getByTestId('plan-approve-button')).toBeDisabled();
    expect(screen.getByTestId('plan-change-button')).toBeDisabled();
  });

  function mockScrollGeometry(list: HTMLElement, { scrollTop, scrollHeight, clientHeight }: { scrollTop: number; scrollHeight: number; clientHeight: number }) {
    Object.defineProperty(list, 'scrollTop', { value: scrollTop, writable: true, configurable: true });
    Object.defineProperty(list, 'scrollHeight', { value: scrollHeight, configurable: true });
    Object.defineProperty(list, 'clientHeight', { value: clientHeight, configurable: true });
  }

  it('does not show the "En yeni mesaja dön" button while the user is at the bottom (Saga #266 AC-5)', () => {
    render(<ChatScreen />);

    expect(screen.queryByTestId('chat-scroll-to-latest-button')).not.toBeInTheDocument();
  });

  it('shows the "En yeni mesaja dön" button once the user scrolls away from the bottom (Saga #266 AC-2, AC-3)', () => {
    render(<ChatScreen />);
    const list = screen.getByTestId('chat-message-list');

    mockScrollGeometry(list, { scrollTop: 0, scrollHeight: 1000, clientHeight: 200 });
    fireEvent.scroll(list);

    expect(screen.getByTestId('chat-scroll-to-latest-button')).toBeVisible();
  });

  it('hides the button again and scrolls to bottom when "En yeni mesaja dön" is clicked (Saga #266 AC-4)', () => {
    render(<ChatScreen />);
    const list = screen.getByTestId('chat-message-list');
    mockScrollGeometry(list, { scrollTop: 0, scrollHeight: 1000, clientHeight: 200 });
    fireEvent.scroll(list);
    expect(screen.getByTestId('chat-scroll-to-latest-button')).toBeVisible();

    fireEvent.click(screen.getByTestId('chat-scroll-to-latest-button'));

    expect(screen.queryByTestId('chat-scroll-to-latest-button')).not.toBeInTheDocument();
  });

  it('hides the button once the user manually scrolls back to the bottom (Saga #266 behaviour contract)', () => {
    render(<ChatScreen />);
    const list = screen.getByTestId('chat-message-list');
    mockScrollGeometry(list, { scrollTop: 0, scrollHeight: 1000, clientHeight: 200 });
    fireEvent.scroll(list);
    expect(screen.getByTestId('chat-scroll-to-latest-button')).toBeVisible();

    mockScrollGeometry(list, { scrollTop: 800, scrollHeight: 1000, clientHeight: 200 });
    fireEvent.scroll(list);

    expect(screen.queryByTestId('chat-scroll-to-latest-button')).not.toBeInTheDocument();
  });

  it('shows the error indicator with a "Tekrar dene" button when planError is set (Saga #267 AC-1)', () => {
    render(<ChatScreen planError="Yerel API'ye ulaşılamadı." />);

    const indicator = screen.getByTestId('plan-error-indicator');
    expect(indicator).toHaveTextContent("Yerel API'ye ulaşılamadı.");
    expect(indicator).toHaveAttribute('role', 'alert');
    expect(screen.getByTestId('plan-retry-button')).toBeVisible();
  });

  it('calls onRetry when "Tekrar dene" is clicked, without any auto-dismiss (Saga #267 AC-2, AC-3)', () => {
    const onRetry = vi.fn();
    render(<ChatScreen planError="Plan üretilemedi." onRetry={onRetry} />);

    fireEvent.click(screen.getByTestId('plan-retry-button'));

    expect(onRetry).toHaveBeenCalledOnce();
    expect(screen.getByTestId('plan-error-indicator')).toBeVisible();
  });

  it('does not show the error indicator when planError is null/omitted (regression)', () => {
    render(<ChatScreen />);

    expect(screen.queryByTestId('plan-error-indicator')).not.toBeInTheDocument();
  });

  it('keeps the textarea and send button enabled while an error is shown (Saga #267 AC-5)', () => {
    render(<ChatScreen planError="Hata oluştu." />);

    const textarea = screen.getByTestId('chat-input-textarea');
    expect(textarea).toBeEnabled();
    fireEvent.change(textarea, { target: { value: 'yeniden deneme mesajı' } });
    expect(screen.getByText('Gönder')).toBeEnabled();
  });

  it('suppresses the error indicator in favour of the loading indicator when both are set (Saga #267 behaviour contract)', () => {
    render(<ChatScreen planError="Eski hata." isGeneratingPlan />);

    expect(screen.getByTestId('plan-loading-indicator')).toBeVisible();
    expect(screen.queryByTestId('plan-error-indicator')).not.toBeInTheDocument();
  });

  it('wraps a user message in a right-aligned blue chat-message-bubble (Saga #260 AC-1, AC-2, AC-3)', () => {
    render(<ChatScreen initialMessages={[{ id: 'u1', role: 'user', text: 'merhaba dünya' }]} />);

    const item = screen.getByTestId('chat-message-u1');
    expect(item).toHaveAttribute('data-role', 'user');
    const bubble = screen.getByTestId('chat-message-bubble-u1');
    expect(bubble).toHaveClass('chat-message-bubble');
    expect(bubble).toHaveTextContent('merhaba dünya');
  });

  it('keeps assistant messages structurally sharing chat-message-bubble without the user-specific role styling target (Saga #260 AC-5)', () => {
    render(<ChatScreen initialMessages={[{ id: 'a1', role: 'assistant', text: 'yanıt metni' }]} />);

    const item = screen.getByTestId('chat-message-a1');
    expect(item).toHaveAttribute('data-role', 'assistant');
    expect(screen.getByTestId('chat-message-bubble-a1')).toHaveClass('chat-message-bubble');
  });

  it('keeps the user bubble left unaffected while the assistant bubble gets the neutral surface (Saga #261 AC-1, AC-2)', () => {
    render(
      <ChatScreen
        initialMessages={[
          { id: 'u1', role: 'user', text: 'kullanıcı mesajı' },
          { id: 'a1', role: 'assistant', text: 'asistan mesajı' },
        ]}
      />,
    );

    expect(screen.getByTestId('chat-message-u1')).toHaveAttribute('data-role', 'user');
    expect(screen.getByTestId('chat-message-a1')).toHaveAttribute('data-role', 'assistant');
    expect(screen.getByTestId('chat-message-bubble-u1')).toHaveClass('chat-message-bubble');
    expect(screen.getByTestId('chat-message-bubble-a1')).toHaveClass('chat-message-bubble');
  });

  it('calls onApprovePlan with the message id when the plan is approved (Saga #273)', () => {
    const onApprovePlan = vi.fn();
    render(
      <ChatScreen
        onApprovePlan={onApprovePlan}
        initialMessages={[
          {
            id: 'p1',
            role: 'assistant',
            text: 'Önerilen plan:',
            plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'approved' },
          },
        ]}
      />,
    );

    fireEvent.click(screen.getByTestId('plan-approve-button'));

    expect(onApprovePlan).toHaveBeenCalledTimes(1);
    expect(onApprovePlan).toHaveBeenCalledWith('p1');
  });

  it('never calls onApprovePlan for a plan that has not passed security (Saga #273, fail-closed)', () => {
    const onApprovePlan = vi.fn();
    render(
      <ChatScreen
        onApprovePlan={onApprovePlan}
        initialMessages={[
          {
            id: 'p1',
            role: 'assistant',
            text: 'Önerilen plan:',
            plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'rejected', rejectionReason: 'reddedildi' },
          },
        ]}
      />,
    );

    fireEvent.click(screen.getByTestId('plan-approve-button'));

    expect(onApprovePlan).not.toHaveBeenCalled();
  });

  it('does not require onApprovePlan to be provided (optional prop, no crash on approve)', () => {
    render(
      <ChatScreen
        initialMessages={[
          {
            id: 'p1',
            role: 'assistant',
            text: 'Önerilen plan:',
            plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'approved' },
          },
        ]}
      />,
    );

    expect(() => fireEvent.click(screen.getByTestId('plan-approve-button'))).not.toThrow();
  });

  it('renders a ResultCard alongside a message that carries a result (Saga #277 AC-1)', () => {
    render(
      <ChatScreen
        initialMessages={[
          {
            id: 'r1',
            role: 'assistant',
            text: 'İşlem tamamlandı:',
            result: { fileCount: 2, destinationFolders: ['2026-08'], status: 'completed' },
          },
        ]}
      />,
    );

    expect(screen.getByTestId('result-card')).toBeVisible();
    expect(screen.getByTestId('result-file-count')).toHaveTextContent('2 dosya işlendi');
  });

  it('does not render a ResultCard when a message has no result (Saga #277 AC-1, regression)', () => {
    render(<ChatScreen initialMessages={[{ id: 'm1', role: 'assistant', text: 'sade metin' }]} />);

    expect(screen.queryByTestId('result-card')).not.toBeInTheDocument();
  });

  it('keeps the chat input enabled while a ResultCard is shown (Saga #277 AC-5)', () => {
    render(
      <ChatScreen
        initialMessages={[
          {
            id: 'r1',
            role: 'assistant',
            text: 'İşlem tamamlandı:',
            result: { fileCount: 2, destinationFolders: ['2026-08'], status: 'completed' },
          },
        ]}
      />,
    );

    expect(screen.getByTestId('chat-input-textarea')).toBeEnabled();
    expect(screen.getByText('Gönder')).toBeDisabled(); // draft boş olduğu için, ResultCard'dan bağımsız
  });

  it('renders messages from the controlled "messages" prop instead of internal state (Saga #287 AC-1)', () => {
    render(<ChatScreen messages={[{ id: 'c1', role: 'assistant', text: 'dışarıdan gelen mesaj' }]} />);

    expect(screen.getByText('dışarıdan gelen mesaj')).toBeVisible();
  });

  it('calls onMessagesChange instead of managing its own state when controlled (Saga #287 AC-1)', () => {
    const onMessagesChange = vi.fn();
    render(<ChatScreen messages={[]} onMessagesChange={onMessagesChange} />);

    fireEvent.change(screen.getByTestId('chat-input-textarea'), { target: { value: 'merhaba' } });
    fireEvent.click(screen.getByText('Gönder'));

    expect(onMessagesChange).toHaveBeenCalledWith([expect.objectContaining({ text: 'merhaba', role: 'user' })]);
    // Controlled modda ChatScreen kendi state'ini güncellemez; yeni mesaj
    // sadece parent messages prop'unu güncellerse görünür.
    expect(screen.queryByText('merhaba')).not.toBeInTheDocument();
  });

  it('keeps existing uncontrolled behaviour unchanged when "messages" prop is omitted (Saga #287 AC-2, regression)', () => {
    render(<ChatScreen />);

    fireEvent.change(screen.getByTestId('chat-input-textarea'), { target: { value: 'uncontrolled mesaj' } });
    fireEvent.click(screen.getByText('Gönder'));

    expect(screen.getByText('uncontrolled mesaj')).toBeVisible();
  });

  it('renders PlanCard outside the message bubble, after it (Saga #260 AC-6, regression)', () => {
    render(
      <ChatScreen
        initialMessages={[
          { id: 'p1', role: 'assistant', text: 'Önerilen plan:', plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 1 }] } },
        ]}
      />,
    );

    const bubble = screen.getByTestId('chat-message-bubble-p1');
    expect(bubble).not.toContainElement(screen.getByTestId('plan-card'));
  });
});

describe('ChatScreen — Geçmişi Temizle (Clear History)', () => {
  it('renders the clear history button when sessionId is provided (AC-1)', () => {
    render(<ChatScreen sessionId="session-123" />);

    expect(screen.getByTestId('chat-clear-history-button')).toBeInTheDocument();
  });

  it('does not render the clear history button when sessionId is not provided (AC-1)', () => {
    render(<ChatScreen />);

    expect(screen.queryByTestId('chat-clear-history-button')).not.toBeInTheDocument();
  });

  it('calls POST /api/transactions/clear-history when the clear history button is clicked (AC-1)', () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ clearedAt: '2026-08-20T12:34:56+00:00' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    try {
      render(<ChatScreen sessionId="session-123" />);

      fireEvent.click(screen.getByTestId('chat-clear-history-button'));

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/transactions/clear-history'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: '{}',
        }),
      );
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('shows success message when clear history succeeds (AC-1)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ clearedAt: '2026-08-20T12:34:56+00:00' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    try {
      render(<ChatScreen sessionId="session-123" />);

      fireEvent.click(screen.getByTestId('chat-clear-history-button'));

      // Success mesajı görünür
      await waitFor(() => {
        expect(screen.getByTestId('chat-clear-history-success-message')).toBeInTheDocument();
      });
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('shows error message when clear history fails (AC-2)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Geçmiş temizlenemedi' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    try {
      render(<ChatScreen sessionId="session-123" />);

      fireEvent.click(screen.getByTestId('chat-clear-history-button'));

      // Error mesajı görünür ve "Geçmiş temizlenemedi" metnini içerir
      await waitFor(() => {
        const errorMsg = screen.getByTestId('chat-clear-history-error-message');
        expect(errorMsg).toBeInTheDocument();
        expect(errorMsg.textContent).toContain('Geçmiş temizlenemedi');
      });
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('shows error message when fetch throws an exception (AC-2)', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('Network error'));
    vi.stubGlobal('fetch', fetchMock);

    try {
      render(<ChatScreen sessionId="session-123" />);

      fireEvent.click(screen.getByTestId('chat-clear-history-button'));

      // Error mesajı gösterilir
      await waitFor(() => {
        expect(screen.getByTestId('chat-clear-history-error-message')).toBeInTheDocument();
      });
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('clears the success message when a new message is sent (AC-3)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ clearedAt: '2026-08-20T12:34:56+00:00' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    try {
      render(<ChatScreen sessionId="session-123" />);

      // Clear history'yi çağır
      fireEvent.click(screen.getByTestId('chat-clear-history-button'));

      // Success mesajı gösterilmeli
      await waitFor(() => {
        expect(screen.getByTestId('chat-clear-history-success-message')).toBeInTheDocument();
      });

      // Yeni mesaj gönder
      const textarea = screen.getByTestId('chat-input-textarea');
      fireEvent.change(textarea, { target: { value: 'yeni mesaj' } });
      fireEvent.click(screen.getByText('Gönder'));

      // Success mesajı temizlenmiş olmalı
      expect(screen.queryByTestId('chat-clear-history-success-message')).not.toBeInTheDocument();
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

describe('ChatScreen — TransactionHistoryPanel entegrasyonu (sol panel, AC-2, AC-8)', () => {
  it('renders the TransactionHistoryPanel (left panel) when sessionId is provided (AC-2, AC-8)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    vi.stubGlobal('fetch', fetchMock);

    try {
      render(<ChatScreen sessionId="session-456" />);

      await waitFor(() => {
        // Sol panel görünür olmalı
        expect(screen.getByTestId('chat-left-panel')).toBeVisible();
      });
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('does not render the TransactionHistoryPanel when sessionId is not provided (AC-2, regression)', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    try {
      render(<ChatScreen />);

      // Sol panel render edilmemeli
      expect(screen.queryByTestId('chat-left-panel')).not.toBeInTheDocument();

      // Fetch de çağrılmamalı
      expect(fetchMock).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('preserves the main-chat-screen data-testid and internal structure when left panel is added (AC-2, regression)', async () => {
    render(<ChatScreen sessionId="session-789" />);

    // Ana sohbet ekranı data-testid'si hala var
    expect(screen.getByTestId('main-chat-screen')).toBeInTheDocument();

    // Mesaj listesi hala var ve erişilebilir
    expect(screen.getByTestId('chat-message-list')).toBeInTheDocument();

    // Input textarea hala var
    expect(screen.getByTestId('chat-input-textarea')).toBeInTheDocument();

    // Send butonu hala var
    expect(screen.getByText('Gönder')).toBeInTheDocument();
  });

  it('allows sending messages independently of the left panel state (AC-2, regression)', async () => {
    const onSendMessage = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    vi.stubGlobal('fetch', fetchMock);

    try {
      render(<ChatScreen sessionId="session-789" onSendMessage={onSendMessage} />);

      // Mesaj gönder
      const textarea = screen.getByTestId('chat-input-textarea');
      fireEvent.change(textarea, { target: { value: 'sol panel ile birlikte mesaj' } });
      fireEvent.click(screen.getByText('Gönder'));

      // Mesaj gösterilmeli
      expect(screen.getByText('sol panel ile birlikte mesaj')).toBeVisible();

      // Callback çağrılmış olmalı
      expect(onSendMessage).toHaveBeenCalledWith(
        expect.objectContaining({ text: 'sol panel ile birlikte mesaj', role: 'user' })
      );

      // Textarea temiz olmalı
      expect(textarea).toHaveValue('');
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('preserves PlanCard rendering alongside the left panel (AC-2, AC-3, regression)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    vi.stubGlobal('fetch', fetchMock);

    try {
      render(
        <ChatScreen
          sessionId="session-789"
          initialMessages={[
            {
              id: 'p1',
              role: 'assistant',
              text: 'Önerilen plan:',
              plan: { steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }], securityStatus: 'approved' },
            },
          ]}
        />
      );

      await waitFor(() => {
        // Sol panel görülüyor
        expect(screen.getByTestId('chat-left-panel')).toBeVisible();

        // Plan Card'ı da görülüyor
        expect(screen.getByTestId('plan-card')).toBeVisible();
      });
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('preserves ResultCard rendering alongside the left panel (AC-2, AC-3, regression)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    vi.stubGlobal('fetch', fetchMock);

    try {
      render(
        <ChatScreen
          sessionId="session-789"
          initialMessages={[
            {
              id: 'r1',
              role: 'assistant',
              text: 'İşlem tamamlandı:',
              result: { fileCount: 5, destinationFolders: ['2026-09'], status: 'completed' },
            },
          ]}
        />
      );

      await waitFor(() => {
        // Sol panel görülüyor
        expect(screen.getByTestId('chat-left-panel')).toBeVisible();

        // Result Card'ı da görülüyor
        expect(screen.getByTestId('result-card')).toBeVisible();
      });
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('maintains fail-closed approve security with the left panel visible (AC-2, AC-3)', async () => {
    const onApprovePlan = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    vi.stubGlobal('fetch', fetchMock);

    try {
      render(
        <ChatScreen
          sessionId="session-789"
          onApprovePlan={onApprovePlan}
          initialMessages={[
            {
              id: 'p1',
              role: 'assistant',
              text: 'Önerilen plan:',
              plan: {
                steps: [{ order: 1, operationType: 'Taşı', targetFolder: 'X', affectedFileCount: 2 }],
                securityStatus: 'rejected',
                rejectionReason: 'reddedildi',
              },
            },
          ]}
        />
      );

      await waitFor(() => {
        // Sol panel render edildi
        expect(screen.getByTestId('chat-left-panel')).toBeVisible();
      });

      // Rejected plan'ı approve etmeye çalış
      fireEvent.click(screen.getByTestId('plan-approve-button'));

      // onApprovePlan çağrılmamalı (fail-closed)
      expect(onApprovePlan).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
