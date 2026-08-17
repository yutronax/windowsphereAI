diff --git a/ui/src/components/chat/ChatScreen.tsx b/ui/src/components/chat/ChatScreen.tsx
index 2b4d5c0..ac22d17 100644
--- a/ui/src/components/chat/ChatScreen.tsx
+++ b/ui/src/components/chat/ChatScreen.tsx
@@ -11,7 +11,15 @@ type Props = {
 export default function ChatScreen({ initialMessages = [], onSendMessage }: Props) {
   const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
   const [draft, setDraft] = useState('');
+  const [editingPlanMessageId, setEditingPlanMessageId] = useState<string | null>(null);
+  const [staleMessageIds, setStaleMessageIds] = useState<Set<string>>(new Set());
   const nextMessageIdRef = useRef(0);
+  const textareaRef = useRef<HTMLTextAreaElement>(null);
+
+  function handleChangePlan(messageId: string) {
+    setEditingPlanMessageId(messageId);
+    textareaRef.current?.focus();
+  }
 
   function sendDraft() {
     const trimmed = draft.trim();
@@ -19,6 +27,10 @@ export default function ChatScreen({ initialMessages = [], onSendMessage }: Prop
     const message: ChatMessage = { id: `msg-${nextMessageIdRef.current++}`, role: 'user', text: trimmed };
     setMessages((current) => [...current, message]);
     setDraft('');
+    if (editingPlanMessageId !== null) {
+      setStaleMessageIds((current) => new Set(current).add(editingPlanMessageId));
+      setEditingPlanMessageId(null);
+    }
     onSendMessage?.(message);
   }
 
@@ -53,6 +65,12 @@ export default function ChatScreen({ initialMessages = [], onSendMessage }: Prop
         .chat-message-item[data-role="user"] {
           margin-left: auto;
         }
+        .chat-edit-plan-hint {
+          margin: 0;
+          padding: 4px 16px 0;
+          font-size: 13px;
+          color: #4B5563;
+        }
         .chat-input-area {
           flex: 0 0 auto;
           border-top: 1px solid #E5E7EB;
@@ -87,12 +105,24 @@ export default function ChatScreen({ initialMessages = [], onSendMessage }: Prop
             data-role={message.role}
           >
             {message.text}
-            {message.plan && <PlanCard plan={message.plan} />}
+            {message.plan && (
+              <PlanCard
+                plan={message.plan}
+                onChangePlan={() => handleChangePlan(message.id)}
+                stale={staleMessageIds.has(message.id)}
+              />
+            )}
           </li>
         ))}
       </ul>
+      {editingPlanMessageId !== null && (
+        <p className="chat-edit-plan-hint" data-testid="chat-edit-plan-hint" aria-live="polite">
+          Planı değiştirmek için ne yapmak istediğinizi yazın.
+        </p>
+      )}
       <div className="chat-input-area">
         <textarea
+          ref={textareaRef}
           data-testid="chat-input-textarea"
           aria-label="Mesaj yaz"
           className="chat-input-textarea"
diff --git a/ui/src/components/chat/PlanCard.tsx b/ui/src/components/chat/PlanCard.tsx
index c214ee1..d3f9074 100644
--- a/ui/src/components/chat/PlanCard.tsx
+++ b/ui/src/components/chat/PlanCard.tsx
@@ -13,13 +13,14 @@ export type Plan = {
   rejectionReason?: string;
 };
 
-type Props = { plan: Plan; onApprove?: () => void };
+type Props = { plan: Plan; onApprove?: () => void; onChangePlan?: () => void; stale?: boolean };
 
 const DEFAULT_REJECTION_MESSAGE = 'Bu plan güvenlik kontrolünden geçemedi.';
 const PENDING_MESSAGE = 'Güvenlik kontrolü bekleniyor…';
+const STALE_MESSAGE = 'Bu plan artık geçerli değil, yeni plan bekleniyor.';
 const STATUS_TEXT_ID = 'plan-approve-status';
 
-export default function PlanCard({ plan, onApprove }: Props) {
+export default function PlanCard({ plan, onApprove, onChangePlan, stale = false }: Props) {
   const [hasApproved, setHasApproved] = useState(false);
   const sortedSteps = [...plan.steps]
     .map((step, index) => ({ step, index }))
@@ -31,8 +32,14 @@ export default function PlanCard({ plan, onApprove }: Props) {
   // etkinleşir. `securityStatus` henüz gelmemişken (undefined) veya "rejected"
   // ise devre dışı kalır — kontrol edilmemiş bir plan asla onaylanabilir
   // durumda gösterilmez (bağımsız red-team bulgusu, 2026-08-17).
-  const canApprove = isApproved && !hasApproved;
-  const statusText = isRejected ? plan.rejectionReason || DEFAULT_REJECTION_MESSAGE : !isApproved ? PENDING_MESSAGE : null;
+  const canApprove = isApproved && !hasApproved && !stale;
+  const statusText = stale
+    ? STALE_MESSAGE
+    : isRejected
+      ? plan.rejectionReason || DEFAULT_REJECTION_MESSAGE
+      : !isApproved
+        ? PENDING_MESSAGE
+        : null;
 
   function handleApprove() {
     if (!canApprove) return;
@@ -96,6 +103,17 @@ export default function PlanCard({ plan, onApprove }: Props) {
         .plan-card-status-text.is-rejected {
           color: #DC2626;
         }
+        .plan-card-change-btn {
+          margin-top: 12px;
+          margin-left: 8px;
+          height: 44px;
+          padding: 0 20px;
+          border-radius: 8px;
+          background-color: #fff;
+          color: #374151;
+          border: 1px solid #D1D5DB;
+          font-size: 16px;
+        }
       `}</style>
       <ol className="plan-card-list">
         {sortedSteps.map(({ step, index }) => (
@@ -118,12 +136,20 @@ export default function PlanCard({ plan, onApprove }: Props) {
       >
         Planı onayla
       </button>
+      <button
+        type="button"
+        className="plan-card-change-btn"
+        data-testid="plan-change-button"
+        onClick={() => onChangePlan?.()}
+      >
+        Planı değiştir
+      </button>
       {statusText && (
         <div aria-live="polite">
           <p
             id={STATUS_TEXT_ID}
-            className={isRejected ? 'plan-card-status-text is-rejected' : 'plan-card-status-text'}
-            data-testid={isRejected ? 'plan-rejection-reason' : 'plan-pending-status'}
+            className={isRejected && !stale ? 'plan-card-status-text is-rejected' : 'plan-card-status-text'}
+            data-testid={stale ? 'plan-stale-status' : isRejected ? 'plan-rejection-reason' : 'plan-pending-status'}
           >
             {statusText}
           </p>
