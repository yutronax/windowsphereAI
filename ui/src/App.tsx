import { useEffect, useRef, useState } from 'react';
import ChatScreen, { type ChatMessage } from './components/chat/ChatScreen';
import { validatePlanResponse } from './components/chat/planValidation';
import type { BackendTransaction } from './lib/transactionResult';
import { toTransactionResult } from './lib/transactionResult';
import type { TransactionResult } from './components/chat/ResultCard';
import OnboardingScreen from './components/onboarding/OnboardingScreen';
import { BACKEND_ORIGIN, waitForBackendHealth } from './lib/backendHealth';

type SetupConfig = { selectedFolder: string };

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

      const rawPlan = await response.json();
      if (isStale()) return;

      // Saga #281: backend'den gelen plan verisi (2xx olsa bile) hiçbir
      // runtime doğrulaması olmadan PlanCard'a verilmiyordu (Saga #262
      // bulgusu). `validatePlanResponse` ile şema doğrulanıyor;
      // geçersizse plan render edilmiyor, mevcut planError/retry
      // mekanizmasına (Saga #267) düşülüyor.
      const validation = validatePlanResponse(rawPlan);
      if (!validation.ok) {
        lastFailedSessionIdRef.current = currentSessionId;
        setPlanError(`Sunucudan geçersiz plan verisi alındı: ${validation.error}`);
        return;
      }

      lastFailedSessionIdRef.current = null;
      const assistantMessage: ChatMessage = {
        id: `assistant-${nextAssistantMessageId++}`,
        role: 'assistant',
        text: validation.plan.steps.length > 0 ? 'Önerilen plan:' : 'Seçili klasörde işlenecek PDF bulunamadı.',
        // Red-team bulgusu (Saga #281): önceden `securityStatus: 'approved'`
        // KOŞULSUZ atanıyordu — backend gelecekte gerçekten 'rejected'
        // dönerse bile sessizce eziliyordu, validatePlanResponse'un
        // securityStatus doğrulaması fiilen ölü koda dönüşüyordu. Artık
        // backend'in AÇIKÇA gönderdiği bir değer varsa o kullanılır,
        // sadece hiç gönderilmemişse (bugünkü backend sözleşmesi) 200
        // yanıtı = whitelist'ten geçti anlamına geldiği için 'approved'a
        // düşülür.
        plan: { ...validation.plan, securityStatus: validation.plan.securityStatus ?? 'approved' },
        // Saga #309 ATDD Soru 2: `Plan` tipi (PlanCard için budanmış)
        // `fileNames`'i taşımıyor — `apply_plan`in ZORUNLU ihtiyaç duyduğu
        // bu alan için HAM (doğrulanmadan önceki) yanıt ayrıca saklanır.
        rawPlan,
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

  async function handleApprovePlan(messageId: string) {
    // Saga #309: onaylanan plan artık gerçekten POST /api/transactions/apply'a
    // gönderilir ve gerçek Orchestrator'ı tetikler (Saga #274/#287'nin
    // kasıtlı no-op'u burada wiring'i tamamlanarak kapatıldı).
    if (!sessionId) return;
    const message = messages.find((m) => m.id === messageId);
    if (!message?.rawPlan) return;

    function markFailed() {
      const failedResult: TransactionResult = { fileCount: 0, destinationFolders: [], status: 'failed' };
      setMessages((current) => current.map((m) => (m.id === messageId ? { ...m, result: failedResult } : m)));
    }

    try {
      const response = await fetch(`${BACKEND_ORIGIN}/api/transactions/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId, plan: message.rawPlan }),
      });
      if (!response.ok) {
        markFailed();
        return;
      }
      const body: BackendTransaction & { id: number } = await response.json();
      const result: TransactionResult = { ...toTransactionResult(body), transactionId: body.id };
      setMessages((current) => current.map((m) => (m.id === messageId ? { ...m, result } : m)));
    } catch {
      markFailed();
    }
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
        sessionId={sessionId ?? undefined}
      />
    );
  }

  return <OnboardingScreen backendStatus={backendStatus} onContinue={setSessionId} onRetry={checkBackend} />;
}
