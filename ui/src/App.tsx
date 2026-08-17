import { useEffect, useRef, useState } from 'react';
import ChatScreen, { type ChatMessage } from './components/chat/ChatScreen';
import OnboardingScreen from './components/onboarding/OnboardingScreen';
import { BACKEND_ORIGIN, waitForBackendHealth } from './lib/backendHealth';

type SetupConfig = { selectedFolder: string };

type PlanStepResponse = {
  order: number;
  operationType: string;
  targetFolder: string;
  affectedFileCount: number;
};

type PlanSkeletonResponse = { steps: PlanStepResponse[] };

let nextAssistantMessageId = 0;

export default function App() {
  const [config, setConfig] = useState<SetupConfig | null | undefined>(undefined);
  const [backendStatus, setBackendStatus] = useState<'ready' | 'starting' | 'backend_timeout'>('starting');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const lastFailedSessionIdRef = useRef<string | null>(null);
  // Saga #287 red-team bulgusu: iki `requestPlan` çağrısı çakışırsa
  // (ör. kullanıcı bir istek sürerken "Tekrar dene"ye basarsa), hangi
  // yanıtın önce geldiği DEĞİL, hangisinin EN SON gönderilen istek
  // olduğu kazanmalı — aksi halde eski bir yanıt yeni bir başarılı
  // planı/hatasını sessizce ezebilir.
  const latestRequestIdRef = useRef(0);

  function checkBackend() {
    setBackendStatus('starting');
    void waitForBackendHealth().then(({ status }) => setBackendStatus(status));
  }

  useEffect(() => {
    fetch(`${BACKEND_ORIGIN}/api/config`)
      .then((response) => (response.ok ? response.json() : null))
      .then((value) => setConfig(value))
      .catch(() => setConfig(null));
    checkBackend();
  }, []);

  async function requestPlan(currentSessionId: string) {
    const requestId = ++latestRequestIdRef.current;
    const isStale = () => latestRequestIdRef.current !== requestId;

    setIsGeneratingPlan(true);
    setPlanError(null);
    try {
      const response = await fetch(`${BACKEND_ORIGIN}/api/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId: currentSessionId }),
      });
      if (isStale()) return;

      if (!response.ok) {
        lastFailedSessionIdRef.current = currentSessionId;
        const body = await response.json().catch(() => null);
        if (isStale()) return;
        setPlanError(body?.detail || 'Plan üretilemedi. Lütfen tekrar deneyin.');
        return;
      }

      lastFailedSessionIdRef.current = null;
      const plan: PlanSkeletonResponse = await response.json();
      if (isStale()) return;
      const assistantMessage: ChatMessage = {
        id: `assistant-${nextAssistantMessageId++}`,
        role: 'assistant',
        text: plan.steps.length > 0 ? 'Önerilen plan:' : 'Seçili klasörde işlenecek PDF bulunamadı.',
        plan: { steps: plan.steps, securityStatus: 'approved' },
      };
      setMessages((current) => [...current, assistantMessage]);
    } catch {
      if (isStale()) return;
      lastFailedSessionIdRef.current = currentSessionId;
      setPlanError('Yerel API’ye ulaşılamadı. Lütfen tekrar deneyin.');
    } finally {
      if (!isStale()) setIsGeneratingPlan(false);
    }
  }

  function handleSendMessage() {
    if (!sessionId) return;
    void requestPlan(sessionId);
  }

  function handleRetry() {
    if (lastFailedSessionIdRef.current) void requestPlan(lastFailedSessionIdRef.current);
  }

  function handleApprovePlan(messageId: string) {
    // Saga #274'ün apply_plan'ı kasıtlı olarak endpoint'siz — gerçek bir
    // Orchestrator çağrısı henüz yok, bu yüzden burada sadece loglanır.
    // Gerçek apply-endpoint wiring'i ayrı bir task (bkz. AI_DEVLOG, Saga #287).
    console.info('Plan onaylandı (henüz Orchestrator’a bağlı değil):', messageId);
  }

  if (config === undefined) return null;
  if (config || sessionId) {
    return (
      <ChatScreen
        messages={messages}
        onMessagesChange={setMessages}
        onSendMessage={handleSendMessage}
        isGeneratingPlan={isGeneratingPlan}
        planError={planError}
        onRetry={handleRetry}
        onApprovePlan={handleApprovePlan}
      />
    );
  }

  return <OnboardingScreen backendStatus={backendStatus} onContinue={setSessionId} onRetry={checkBackend} />;
}
