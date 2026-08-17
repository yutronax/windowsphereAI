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
});
