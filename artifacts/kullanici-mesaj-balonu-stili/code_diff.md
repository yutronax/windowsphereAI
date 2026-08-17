diff --git a/ui/src/components/chat/ChatScreen.tsx b/ui/src/components/chat/ChatScreen.tsx
index 8288830..9343e02 100644
--- a/ui/src/components/chat/ChatScreen.tsx
+++ b/ui/src/components/chat/ChatScreen.tsx
@@ -112,6 +112,16 @@ export default function ChatScreen({
         .chat-message-item[data-role="user"] {
           margin-left: auto;
         }
+        .chat-message-bubble {
+          padding: 16px;
+          border-radius: 14px;
+          max-width: 65ch;
+          overflow-wrap: break-word;
+        }
+        .chat-message-item[data-role="user"] .chat-message-bubble {
+          background-color: #1E3A8A;
+          color: #fff;
+        }
         .chat-scroll-to-latest-button {
           align-self: center;
           margin: 4px auto;
@@ -223,7 +233,9 @@ export default function ChatScreen({
             data-testid={`chat-message-${message.id}`}
             data-role={message.role}
           >
-            {message.text}
+            <div className="chat-message-bubble" data-testid={`chat-message-bubble-${message.id}`}>
+              {message.text}
+            </div>
             {message.plan && (
               <PlanCard
                 plan={message.plan}
