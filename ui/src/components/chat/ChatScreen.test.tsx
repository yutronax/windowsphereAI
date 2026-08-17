import { fireEvent, render, screen } from '@testing-library/react';
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
