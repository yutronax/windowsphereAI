import { useRef, useState, type KeyboardEvent } from 'react';
import PlanCard, { type Plan } from './PlanCard';

export type ChatMessage = { id: string; role: 'user' | 'assistant'; text: string; plan?: Plan };

type Props = {
  initialMessages?: ChatMessage[];
  onSendMessage?: (message: ChatMessage) => void;
  isGeneratingPlan?: boolean;
};

export default function ChatScreen({ initialMessages = [], onSendMessage, isGeneratingPlan = false }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [draft, setDraft] = useState('');
  const [editingPlanMessageId, setEditingPlanMessageId] = useState<string | null>(null);
  const [staleMessageIds, setStaleMessageIds] = useState<Set<string>>(new Set());
  const nextMessageIdRef = useRef(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleChangePlan(messageId: string) {
    setEditingPlanMessageId(messageId);
    textareaRef.current?.focus();
  }

  function sendDraft() {
    const trimmed = draft.trim();
    if (trimmed === '') return;
    const message: ChatMessage = { id: `msg-${nextMessageIdRef.current++}`, role: 'user', text: trimmed };
    setMessages((current) => [...current, message]);
    setDraft('');
    if (editingPlanMessageId !== null) {
      setStaleMessageIds((current) => new Set(current).add(editingPlanMessageId));
      setEditingPlanMessageId(null);
    }
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
        .chat-edit-plan-hint {
          margin: 0;
          padding: 4px 16px 0;
          font-size: 13px;
          color: #4B5563;
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
        .chat-input-textarea:disabled {
          background-color: #F3F4F6;
          cursor: not-allowed;
        }
        .plan-loading-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 4px 16px;
          font-size: 14px;
          color: #4B5563;
        }
        .plan-loading-dots {
          display: inline-flex;
          gap: 4px;
        }
        .plan-loading-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background-color: #6B7280;
          animation: plan-loading-bounce 1.2s infinite ease-in-out both;
        }
        .plan-loading-dot:nth-child(1) { animation-delay: -0.24s; }
        .plan-loading-dot:nth-child(2) { animation-delay: -0.12s; }
        @keyframes plan-loading-bounce {
          0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
        @media (prefers-reduced-motion: reduce) {
          .plan-loading-dot {
            animation: none;
          }
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
            {message.plan && (
              <PlanCard
                plan={message.plan}
                onChangePlan={() => handleChangePlan(message.id)}
                stale={staleMessageIds.has(message.id)}
                isGeneratingPlan={isGeneratingPlan}
              />
            )}
          </li>
        ))}
      </ul>
      {editingPlanMessageId !== null && (
        <p className="chat-edit-plan-hint" data-testid="chat-edit-plan-hint" aria-live="polite">
          Planı değiştirmek için ne yapmak istediğinizi yazın.
        </p>
      )}
      {isGeneratingPlan && (
        <div className="plan-loading-indicator" data-testid="plan-loading-indicator" aria-live="polite">
          <span className="plan-loading-dots" aria-hidden="true">
            <span className="plan-loading-dot" />
            <span className="plan-loading-dot" />
            <span className="plan-loading-dot" />
          </span>
          Plan hazırlanıyor…
        </div>
      )}
      <div className="chat-input-area">
        <textarea
          ref={textareaRef}
          data-testid="chat-input-textarea"
          aria-label="Mesaj yaz"
          className="chat-input-textarea"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isGeneratingPlan}
        />
        <button type="button" onClick={sendDraft} disabled={draft.trim() === '' || isGeneratingPlan}>Gönder</button>
      </div>
    </main>
  );
}
