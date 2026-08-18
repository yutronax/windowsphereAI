import { useEffect, useRef, useState, type KeyboardEvent, type UIEvent } from 'react';
import PlanCard, { type Plan } from './PlanCard';
import ResultCard, { type TransactionResult } from './ResultCard';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  plan?: Plan;
  result?: TransactionResult;
  // Saga #309: `/api/plan`'ın HAM (budanmadan önceki) JSON gövdesi —
  // sadece App.tsx tarafından `/api/transactions/apply`e geri göndermek
  // için saklanır, ChatScreen/PlanCard bunu RENDER ETMEZ (bkz. atdd.md
  // Soru 2, plan.md).
  rawPlan?: Record<string, unknown>;
};

type Props = {
  initialMessages?: ChatMessage[];
  // Saga #287: `messages`/`onMessagesChange` VERİLİRSE ChatScreen
  // CONTROLLED çalışır (App.tsx'in asenkron bir /api/plan yanıtını
  // sohbete yansıtabilmesi için — ChatScreen öncesinde mesaj listesini
  // tamamen kendi iç state'inde tutuyordu, dışarıdan mesaj eklemenin
  // hiçbir yolu yoktu). VERİLMEZSE (mevcut tüm testler) davranış
  // uncontrolled ve eskisiyle birebir aynı kalır — dar kapsam, regresyon
  // yok.
  messages?: ChatMessage[];
  onMessagesChange?: (messages: ChatMessage[]) => void;
  onSendMessage?: (message: ChatMessage) => void;
  isGeneratingPlan?: boolean;
  planError?: string | null;
  onRetry?: () => void;
  // Saga #273: PlanCard'ın "Planı onayla" butonu SADECE bu callback
  // üzerinden dışarı bildirim yapar — Orchestrator'ı çağırmak (henüz
  // yazılmadı, Saga #274) bu callback'in sorumluluğu, kullanıcı gerçekten
  // tıklamadan asla tetiklenmez (PlanCard'ın fail-closed canApprove
  // mantığıyla birlikte).
  onApprovePlan?: (messageId: string) => void;
};

const BOTTOM_THRESHOLD_PX = 24;

export default function ChatScreen({
  initialMessages = [],
  messages: controlledMessages,
  onMessagesChange,
  onSendMessage,
  isGeneratingPlan = false,
  planError = null,
  onRetry,
  onApprovePlan,
}: Props) {
  const isControlled = controlledMessages !== undefined;
  const [internalMessages, setInternalMessages] = useState<ChatMessage[]>(initialMessages);
  const messages = isControlled ? controlledMessages : internalMessages;

  function updateMessages(updater: (current: ChatMessage[]) => ChatMessage[]) {
    if (isControlled) {
      onMessagesChange?.(updater(messages));
    } else {
      setInternalMessages(updater);
    }
  }

  const [draft, setDraft] = useState('');
  const [editingPlanMessageId, setEditingPlanMessageId] = useState<string | null>(null);
  const [staleMessageIds, setStaleMessageIds] = useState<Set<string>>(new Set());
  const [isAtBottom, setIsAtBottom] = useState(true);
  const nextMessageIdRef = useRef(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  function scrollToBottom(smooth = true) {
    const list = listRef.current;
    if (!list) return;
    if (typeof list.scrollTo === 'function') {
      list.scrollTo({ top: list.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
    } else {
      list.scrollTop = list.scrollHeight;
    }
  }

  function handleScroll(e: UIEvent<HTMLUListElement>) {
    const list = e.currentTarget;
    const distanceFromBottom = list.scrollHeight - list.scrollTop - list.clientHeight;
    setIsAtBottom(distanceFromBottom <= BOTTOM_THRESHOLD_PX);
  }

  function handleReturnToLatest() {
    scrollToBottom();
    setIsAtBottom(true);
  }

  // Sayı yerine bir "son mesaj parmak izi" kullanılır: mesaj sayısı
  // değişmeden bir mesajın içeriği (ör. plan.securityStatus approved/rejected
  // olduğunda) güncellenirse de en alttaki kullanıcı için otomatik kaydırma
  // tetiklenmeli — sadece messages.length'e bakmak bu durumu kaçırır
  // (red-team bulgusu, Saga #266).
  const lastMessage = messages[messages.length - 1];
  const scrollTriggerKey = `${messages.length}:${lastMessage?.id ?? ''}:${lastMessage?.plan?.securityStatus ?? ''}:${lastMessage?.text.length ?? ''}`;

  useEffect(() => {
    if (isAtBottom) scrollToBottom();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scrollTriggerKey]);

  function handleChangePlan(messageId: string) {
    setEditingPlanMessageId(messageId);
    textareaRef.current?.focus();
  }

  function sendDraft() {
    const trimmed = draft.trim();
    if (trimmed === '') return;
    const message: ChatMessage = { id: `msg-${nextMessageIdRef.current++}`, role: 'user', text: trimmed };
    updateMessages((current) => [...current, message]);
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
        .chat-message-bubble {
          padding: 16px;
          border-radius: 14px;
          max-width: 65ch;
          overflow-wrap: break-word;
          line-height: 1.5;
        }
        .chat-message-item[data-role="user"] .chat-message-bubble {
          background-color: #1E3A8A;
          color: #fff;
        }
        .chat-message-item[data-role="assistant"] .chat-message-bubble {
          background-color: #F3F4F6;
          color: #111827;
        }
        .chat-scroll-to-latest-button {
          align-self: center;
          margin: 4px auto;
          height: 32px;
          padding: 0 16px;
          border-radius: 16px;
          background-color: #111827;
          color: #fff;
          border: none;
          font-size: 13px;
          cursor: pointer;
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
        .plan-error-indicator {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin: 4px 16px 0;
          padding: 8px 12px;
          border-radius: 8px;
          background-color: #FEF2F2;
          border: 1px solid #FCA5A5;
          color: #B91C1C;
          font-size: 14px;
        }
        .plan-retry-button {
          flex: 0 0 auto;
          height: 32px;
          padding: 0 14px;
          border-radius: 8px;
          background-color: #DC2626;
          color: #fff;
          border: none;
          font-size: 13px;
          cursor: pointer;
        }
      `}</style>
      <ul
        ref={listRef}
        className="chat-message-list"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label="Sohbet geçmişi"
        data-testid="chat-message-list"
        onScroll={handleScroll}
      >
        {messages.map((message) => (
          <li
            key={message.id}
            className="chat-message-item"
            data-testid={`chat-message-${message.id}`}
            data-role={message.role}
          >
            <div className="chat-message-bubble" data-testid={`chat-message-bubble-${message.id}`}>
              {message.text}
            </div>
            {message.plan && (
              <PlanCard
                plan={message.plan}
                onChangePlan={() => handleChangePlan(message.id)}
                onApprove={() => onApprovePlan?.(message.id)}
                stale={staleMessageIds.has(message.id)}
                isGeneratingPlan={isGeneratingPlan}
              />
            )}
            {message.result && <ResultCard result={message.result} />}
          </li>
        ))}
      </ul>
      {!isAtBottom && (
        <button
          type="button"
          className="chat-scroll-to-latest-button"
          data-testid="chat-scroll-to-latest-button"
          onClick={handleReturnToLatest}
        >
          En yeni mesaja dön
        </button>
      )}
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
      {planError && !isGeneratingPlan && (
        <div className="plan-error-indicator" data-testid="plan-error-indicator" role="alert">
          <span>{planError}</span>
          <button
            type="button"
            className="plan-retry-button"
            data-testid="plan-retry-button"
            onClick={() => onRetry?.()}
          >
            Tekrar dene
          </button>
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
