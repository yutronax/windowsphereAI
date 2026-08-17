diff --git a/ui/src/components/chat/ChatScreen.tsx b/ui/src/components/chat/ChatScreen.tsx
index 9343e02..75a874d 100644
--- a/ui/src/components/chat/ChatScreen.tsx
+++ b/ui/src/components/chat/ChatScreen.tsx
@@ -117,11 +117,16 @@ export default function ChatScreen({
           border-radius: 14px;
           max-width: 65ch;
           overflow-wrap: break-word;
+          line-height: 1.5;
         }
         .chat-message-item[data-role="user"] .chat-message-bubble {
           background-color: #1E3A8A;
           color: #fff;
         }
+        .chat-message-item[data-role="assistant"] .chat-message-bubble {
+          background-color: #F3F4F6;
+          color: #111827;
+        }
         .chat-scroll-to-latest-button {
           align-self: center;
           margin: 4px auto;
