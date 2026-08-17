import { useRef, useState, type KeyboardEvent } from 'react';
import PlanCard, { type Plan } from './PlanCard';

export type ChatMessage = { id: string; role: 'user' | 'assistant'; text: string; plan?: Plan };

type Props = {
  initialMessages?: ChatMessage[];
  onSendMessage?: (message: ChatMessage) => void;
};

export default function ChatScreen({ initialMessages = [], onSendMessage }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [draft, setDraft] = useState('');
  const nextMessageIdRef = useRef(0);

  function sendDraft() {
    const trimmed = draft.trim();
    if (trimmed === '') return;
    const message: ChatMessage = { id: `msg-${nextMessageIdRef.current++}`, role: 'user', text: trimmed };
    setMessages((current) => [...current, message]);
    setDraft('');
    onSendMessage?.(message);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendDraft();
    }
  }

  return (
    <main data-testid="main-chat-screen" className="chat-screen">
      <style>{`
        .chat-screen {
          display: flex;
          flex-direction: column;
          height: 100vh;
          box-sizing: border-box;
        }
        .chat-message-list {
          flex: 1 1 auto;
          overflow-y: auto;
          list-style: none;
          margin: 0;
          padding: 16px;
        }
        .chat-message-item {
          margin-bottom: 12px;
          user-select: text;
          max-width: 70%;
        }
        .chat-message-item[data-role="user"] {
          margin-left: auto;
        }
        .chat-input-area {
          flex: 0 0 auto;
          border-top: 1px solid #E5E7EB;
          padding: 12px 16px;
          display: flex;
          gap: 8px;
        }
        .chat-input-textarea {
          flex: 1;
          resize: none;
          min-height: 44px;
          border-radius: 8px;
          border: 1px solid #E5E7EB;
          padding: 8px 12px;
          font-size: 16px;
          box-sizing: border-box;
        }
      `}</style>
      <ul
        className="chat-message-list"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label="Sohbet geçmişi"
        data-testid="chat-message-list"
      >
        {messages.map((message) => (
          <li
            key={message.id}
            className="chat-message-item"
            data-testid={`chat-message-${message.id}`}
            data-role={message.role}
          >
            {message.text}
            {message.plan && <PlanCard plan={message.plan} />}
          </li>
        ))}
      </ul>
      <div className="chat-input-area">
        <textarea
          data-testid="chat-input-textarea"
          aria-label="Mesaj yaz"
          className="chat-input-textarea"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button type="button" onClick={sendDraft} disabled={draft.trim() === ''}>Gönder</button>
      </div>
    </main>
  );
}
