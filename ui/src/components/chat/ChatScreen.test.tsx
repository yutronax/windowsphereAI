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
});
