diff --git a/ui/src/components/chat/ChatScreen.tsx b/ui/src/components/chat/ChatScreen.tsx
index 3539cde..8288830 100644
--- a/ui/src/components/chat/ChatScreen.tsx
+++ b/ui/src/components/chat/ChatScreen.tsx
@@ -7,11 +7,19 @@ type Props = {
   initialMessages?: ChatMessage[];
   onSendMessage?: (message: ChatMessage) => void;
   isGeneratingPlan?: boolean;
+  planError?: string | null;
+  onRetry?: () => void;
 };
 
 const BOTTOM_THRESHOLD_PX = 24;
 
-export default function ChatScreen({ initialMessages = [], onSendMessage, isGeneratingPlan = false }: Props) {
+export default function ChatScreen({
+  initialMessages = [],
+  onSendMessage,
+  isGeneratingPlan = false,
+  planError = null,
+  onRetry,
+}: Props) {
   const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
   const [draft, setDraft] = useState('');
   const [editingPlanMessageId, setEditingPlanMessageId] = useState<string | null>(null);
@@ -173,6 +181,30 @@ export default function ChatScreen({ initialMessages = [], onSendMessage, isGene
             animation: none;
           }
         }
+        .plan-error-indicator {
+          display: flex;
+          align-items: center;
+          justify-content: space-between;
+          gap: 12px;
+          margin: 4px 16px 0;
+          padding: 8px 12px;
+          border-radius: 8px;
+          background-color: #FEF2F2;
+          border: 1px solid #FCA5A5;
+          color: #B91C1C;
+          font-size: 14px;
+        }
+        .plan-retry-button {
+          flex: 0 0 auto;
+          height: 32px;
+          padding: 0 14px;
+          border-radius: 8px;
+          background-color: #DC2626;
+          color: #fff;
+          border: none;
+          font-size: 13px;
+          cursor: pointer;
+        }
       `}</style>
       <ul
         ref={listRef}
@@ -228,6 +260,19 @@ export default function ChatScreen({ initialMessages = [], onSendMessage, isGene
           Plan hazırlanıyor…
         </div>
       )}
+      {planError && !isGeneratingPlan && (
+        <div className="plan-error-indicator" data-testid="plan-error-indicator" role="alert">
+          <span>{planError}</span>
+          <button
+            type="button"
+            className="plan-retry-button"
+            data-testid="plan-retry-button"
+            onClick={() => onRetry?.()}
+          >
+            Tekrar dene
+          </button>
+        </div>
+      )}
       <div className="chat-input-area">
         <textarea
           ref={textareaRef}
