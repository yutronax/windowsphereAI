diff --git a/ui/src/components/chat/ChatScreen.tsx b/ui/src/components/chat/ChatScreen.tsx
index ac22d17..557d1e3 100644
--- a/ui/src/components/chat/ChatScreen.tsx
+++ b/ui/src/components/chat/ChatScreen.tsx
@@ -6,9 +6,10 @@ export type ChatMessage = { id: string; role: 'user' | 'assistant'; text: string
 type Props = {
   initialMessages?: ChatMessage[];
   onSendMessage?: (message: ChatMessage) => void;
+  isGeneratingPlan?: boolean;
 };
 
-export default function ChatScreen({ initialMessages = [], onSendMessage }: Props) {
+export default function ChatScreen({ initialMessages = [], onSendMessage, isGeneratingPlan = false }: Props) {
   const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
   const [draft, setDraft] = useState('');
   const [editingPlanMessageId, setEditingPlanMessageId] = useState<string | null>(null);
@@ -88,6 +89,40 @@ export default function ChatScreen({ initialMessages = [], onSendMessage }: Prop
           font-size: 16px;
           box-sizing: border-box;
         }
+        .chat-input-textarea:disabled {
+          background-color: #F3F4F6;
+          cursor: not-allowed;
+        }
+        .plan-loading-indicator {
+          display: flex;
+          align-items: center;
+          gap: 8px;
+          padding: 4px 16px;
+          font-size: 14px;
+          color: #4B5563;
+        }
+        .plan-loading-dots {
+          display: inline-flex;
+          gap: 4px;
+        }
+        .plan-loading-dot {
+          width: 6px;
+          height: 6px;
+          border-radius: 50%;
+          background-color: #6B7280;
+          animation: plan-loading-bounce 1.2s infinite ease-in-out both;
+        }
+        .plan-loading-dot:nth-child(1) { animation-delay: -0.24s; }
+        .plan-loading-dot:nth-child(2) { animation-delay: -0.12s; }
+        @keyframes plan-loading-bounce {
+          0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
+          40% { opacity: 1; transform: scale(1); }
+        }
+        @media (prefers-reduced-motion: reduce) {
+          .plan-loading-dot {
+            animation: none;
+          }
+        }
       `}</style>
       <ul
         className="chat-message-list"
@@ -110,6 +145,7 @@ export default function ChatScreen({ initialMessages = [], onSendMessage }: Prop
                 plan={message.plan}
                 onChangePlan={() => handleChangePlan(message.id)}
                 stale={staleMessageIds.has(message.id)}
+                isGeneratingPlan={isGeneratingPlan}
               />
             )}
           </li>
@@ -120,6 +156,16 @@ export default function ChatScreen({ initialMessages = [], onSendMessage }: Prop
           Planı değiştirmek için ne yapmak istediğinizi yazın.
         </p>
       )}
+      {isGeneratingPlan && (
+        <div className="plan-loading-indicator" data-testid="plan-loading-indicator" aria-live="polite">
+          <span className="plan-loading-dots" aria-hidden="true">
+            <span className="plan-loading-dot" />
+            <span className="plan-loading-dot" />
+            <span className="plan-loading-dot" />
+          </span>
+          Plan hazırlanıyor…
+        </div>
+      )}
       <div className="chat-input-area">
         <textarea
           ref={textareaRef}
@@ -129,8 +175,9 @@ export default function ChatScreen({ initialMessages = [], onSendMessage }: Prop
           value={draft}
           onChange={(e) => setDraft(e.target.value)}
           onKeyDown={handleKeyDown}
+          disabled={isGeneratingPlan}
         />
-        <button type="button" onClick={sendDraft} disabled={draft.trim() === ''}>Gönder</button>
+        <button type="button" onClick={sendDraft} disabled={draft.trim() === '' || isGeneratingPlan}>Gönder</button>
       </div>
     </main>
   );
diff --git a/ui/src/components/chat/PlanCard.tsx b/ui/src/components/chat/PlanCard.tsx
index d3f9074..f52f2e9 100644
--- a/ui/src/components/chat/PlanCard.tsx
+++ b/ui/src/components/chat/PlanCard.tsx
@@ -13,14 +13,20 @@ export type Plan = {
   rejectionReason?: string;
 };
 
-type Props = { plan: Plan; onApprove?: () => void; onChangePlan?: () => void; stale?: boolean };
+type Props = {
+  plan: Plan;
+  onApprove?: () => void;
+  onChangePlan?: () => void;
+  stale?: boolean;
+  isGeneratingPlan?: boolean;
+};
 
 const DEFAULT_REJECTION_MESSAGE = 'Bu plan güvenlik kontrolünden geçemedi.';
 const PENDING_MESSAGE = 'Güvenlik kontrolü bekleniyor…';
 const STALE_MESSAGE = 'Bu plan artık geçerli değil, yeni plan bekleniyor.';
 const STATUS_TEXT_ID = 'plan-approve-status';
 
-export default function PlanCard({ plan, onApprove, onChangePlan, stale = false }: Props) {
+export default function PlanCard({ plan, onApprove, onChangePlan, stale = false, isGeneratingPlan = false }: Props) {
   const [hasApproved, setHasApproved] = useState(false);
   const sortedSteps = [...plan.steps]
     .map((step, index) => ({ step, index }))
@@ -32,7 +38,11 @@ export default function PlanCard({ plan, onApprove, onChangePlan, stale = false
   // etkinleşir. `securityStatus` henüz gelmemişken (undefined) veya "rejected"
   // ise devre dışı kalır — kontrol edilmemiş bir plan asla onaylanabilir
   // durumda gösterilmez (bağımsız red-team bulgusu, 2026-08-17).
-  const canApprove = isApproved && !hasApproved && !stale;
+  // Yeni bir plan üretilirken (isGeneratingPlan) bu plan üzerinde onay/değiştir
+  // eylemi de kilitlenir — aksi halde "Plan hazırlanıyor…" ile "Planı değiştirmek
+  // için yazın" ipucu aynı anda çelişkili biçimde görünebilir (red-team bulgusu,
+  // Saga #265).
+  const canApprove = isApproved && !hasApproved && !stale && !isGeneratingPlan;
   const statusText = stale
     ? STALE_MESSAGE
     : isRejected
@@ -140,6 +150,7 @@ export default function PlanCard({ plan, onApprove, onChangePlan, stale = false
         type="button"
         className="plan-card-change-btn"
         data-testid="plan-change-button"
+        disabled={isGeneratingPlan}
         onClick={() => onChangePlan?.()}
       >
         Planı değiştir
