diff --git a/ui/src/components/chat/ChatScreen.tsx b/ui/src/components/chat/ChatScreen.tsx
index 557d1e3..3539cde 100644
--- a/ui/src/components/chat/ChatScreen.tsx
+++ b/ui/src/components/chat/ChatScreen.tsx
@@ -1,4 +1,4 @@
-import { useRef, useState, type KeyboardEvent } from 'react';
+import { useEffect, useRef, useState, type KeyboardEvent, type UIEvent } from 'react';
 import PlanCard, { type Plan } from './PlanCard';
 
 export type ChatMessage = { id: string; role: 'user' | 'assistant'; text: string; plan?: Plan };
@@ -9,13 +9,51 @@ type Props = {
   isGeneratingPlan?: boolean;
 };
 
+const BOTTOM_THRESHOLD_PX = 24;
+
 export default function ChatScreen({ initialMessages = [], onSendMessage, isGeneratingPlan = false }: Props) {
   const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
   const [draft, setDraft] = useState('');
   const [editingPlanMessageId, setEditingPlanMessageId] = useState<string | null>(null);
   const [staleMessageIds, setStaleMessageIds] = useState<Set<string>>(new Set());
+  const [isAtBottom, setIsAtBottom] = useState(true);
   const nextMessageIdRef = useRef(0);
   const textareaRef = useRef<HTMLTextAreaElement>(null);
+  const listRef = useRef<HTMLUListElement>(null);
+
+  function scrollToBottom(smooth = true) {
+    const list = listRef.current;
+    if (!list) return;
+    if (typeof list.scrollTo === 'function') {
+      list.scrollTo({ top: list.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
+    } else {
+      list.scrollTop = list.scrollHeight;
+    }
+  }
+
+  function handleScroll(e: UIEvent<HTMLUListElement>) {
+    const list = e.currentTarget;
+    const distanceFromBottom = list.scrollHeight - list.scrollTop - list.clientHeight;
+    setIsAtBottom(distanceFromBottom <= BOTTOM_THRESHOLD_PX);
+  }
+
+  function handleReturnToLatest() {
+    scrollToBottom();
+    setIsAtBottom(true);
+  }
+
+  // Sayı yerine bir "son mesaj parmak izi" kullanılır: mesaj sayısı
+  // değişmeden bir mesajın içeriği (ör. plan.securityStatus approved/rejected
+  // olduğunda) güncellenirse de en alttaki kullanıcı için otomatik kaydırma
+  // tetiklenmeli — sadece messages.length'e bakmak bu durumu kaçırır
+  // (red-team bulgusu, Saga #266).
+  const lastMessage = messages[messages.length - 1];
+  const scrollTriggerKey = `${messages.length}:${lastMessage?.id ?? ''}:${lastMessage?.plan?.securityStatus ?? ''}:${lastMessage?.text.length ?? ''}`;
+
+  useEffect(() => {
+    if (isAtBottom) scrollToBottom();
+    // eslint-disable-next-line react-hooks/exhaustive-deps
+  }, [scrollTriggerKey]);
 
   function handleChangePlan(messageId: string) {
     setEditingPlanMessageId(messageId);
@@ -66,6 +104,18 @@ export default function ChatScreen({ initialMessages = [], onSendMessage, isGene
         .chat-message-item[data-role="user"] {
           margin-left: auto;
         }
+        .chat-scroll-to-latest-button {
+          align-self: center;
+          margin: 4px auto;
+          height: 32px;
+          padding: 0 16px;
+          border-radius: 16px;
+          background-color: #111827;
+          color: #fff;
+          border: none;
+          font-size: 13px;
+          cursor: pointer;
+        }
         .chat-edit-plan-hint {
           margin: 0;
           padding: 4px 16px 0;
@@ -125,12 +175,14 @@ export default function ChatScreen({ initialMessages = [], onSendMessage, isGene
         }
       `}</style>
       <ul
+        ref={listRef}
         className="chat-message-list"
         role="log"
         aria-live="polite"
         aria-relevant="additions"
         aria-label="Sohbet geçmişi"
         data-testid="chat-message-list"
+        onScroll={handleScroll}
       >
         {messages.map((message) => (
           <li
@@ -151,6 +203,16 @@ export default function ChatScreen({ initialMessages = [], onSendMessage, isGene
           </li>
         ))}
       </ul>
+      {!isAtBottom && (
+        <button
+          type="button"
+          className="chat-scroll-to-latest-button"
+          data-testid="chat-scroll-to-latest-button"
+          onClick={handleReturnToLatest}
+        >
+          En yeni mesaja dön
+        </button>
+      )}
       {editingPlanMessageId !== null && (
         <p className="chat-edit-plan-hint" data-testid="chat-edit-plan-hint" aria-live="polite">
           Planı değiştirmek için ne yapmak istediğinizi yazın.
