diff --git a/ui/src/components/chat/ChatScreen.tsx b/ui/src/components/chat/ChatScreen.tsx
index 4761a5c..2b4d5c0 100644
--- a/ui/src/components/chat/ChatScreen.tsx
+++ b/ui/src/components/chat/ChatScreen.tsx
@@ -1,6 +1,7 @@
 import { useRef, useState, type KeyboardEvent } from 'react';
+import PlanCard, { type Plan } from './PlanCard';
 
-export type ChatMessage = { id: string; role: 'user' | 'assistant'; text: string };
+export type ChatMessage = { id: string; role: 'user' | 'assistant'; text: string; plan?: Plan };
 
 type Props = {
   initialMessages?: ChatMessage[];
@@ -86,6 +87,7 @@ export default function ChatScreen({ initialMessages = [], onSendMessage }: Prop
             data-role={message.role}
           >
             {message.text}
+            {message.plan && <PlanCard plan={message.plan} />}
           </li>
         ))}
       </ul>
--- new file: PlanCard.tsx ---
export type PlanStep = {
  order: number;
  operationType: string;
  targetFolder: string;
  affectedFileCount: number;
};

export type Plan = { steps: PlanStep[] };

type Props = { plan: Plan };

export default function PlanCard({ plan }: Props) {
  const sortedSteps = [...plan.steps]
    .map((step, index) => ({ step, index }))
    .sort((a, b) => a.step.order - b.step.order || a.index - b.index);

  return (
    <section className="plan-card" data-testid="plan-card" aria-label="Önerilen plan">
      <style>{`
        .plan-card {
          border: 1px solid #E5E7EB;
          border-radius: 12px;
          padding: 12px 16px;
          margin-top: 8px;
          background-color: #FAFAFA;
        }
        .plan-card-list {
          margin: 0;
          padding-left: 20px;
        }
        .plan-card-step {
          margin-bottom: 8px;
        }
        .plan-card-step:last-child {
          margin-bottom: 0;
        }
        .plan-card-operation {
          font-weight: 600;
        }
        .plan-card-meta {
          color: #4B5563;
          font-size: 14px;
        }
      `}</style>
      <ol className="plan-card-list">
        {sortedSteps.map(({ step, index }) => (
          <li key={`${step.order}-${index}`} className="plan-card-step" data-testid={`plan-step-${step.order}-${index}`}>
            <span className="plan-card-operation">{step.operationType}</span>
            {' — '}
            <span className="plan-card-meta">
              {step.targetFolder} ({step.affectedFileCount} dosya)
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
