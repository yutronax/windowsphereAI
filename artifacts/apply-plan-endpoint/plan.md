# Plan — apply-plan-endpoint (Saga #309)

## Backend

### `backend/models.py`
- Yeni `ApplyPlanRequest(BaseModel)`: `sessionId: str` (aynı
  `session_id_not_blank` validator'ı `PlanRequest`den kopyalanır ya da
  paylaşılan bir helper'a çıkarılır — küçük ölçek, doğrudan kopyalamak
  yeterli), `plan: PlanSkeleton`.
- Yeni `AppliedFileOperation(BaseModel)`: `destination_path: str`,
  `status: str` (frontend `transactionResult.ts`'in `BackendFileOperation`
  ile birebir eşleşmeli — alan adları AYNEN `destination_path`/`status`,
  camelCase'e ÇEVRİLMEZ, çünkü frontend zaten bu snake_case alanları
  bekliyor, Saga #277 sözleşmesi).
- Yeni `TransactionApplyResponse(BaseModel)`: `id: int`, `status: str`,
  `operations: list[AppliedFileOperation]`.

### `backend/main.py`
- `from backend.orchestrator import PlanApplicationError, TransactionRevertError, apply_plan, revert_transaction` importuna `PlanApplicationError`, `apply_plan` eklenir.
- `from backend.models import ApplyPlanRequest, TransactionApplyResponse` eklenir.
- `from backend.models import OperationType` (LIST kontrolü için) eklenir.
- Yeni dependency:
  ```python
  def get_session_for_apply(payload: ApplyPlanRequest) -> SessionContext:
      """`get_session_or_404` ile aynı mantık ama farklı body şeması
      (ApplyPlanRequest, PlanRequest değil) olduğu için ayrı — ikisini
      birleştiren bir Protocol/generic burada gereksiz karmaşıklık
      olurdu (dar kapsam ilkesi, saga-oto atdd.md Soru 3)."""
      session = _sessions.get(payload.sessionId)
      if session is None:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum bulunamadı")
      return session
  ```
- Yeni endpoint:
  ```python
  @app.post("/api/transactions/apply")
  def apply_plan_endpoint(
      payload: ApplyPlanRequest,
      session: SessionContext = Depends(get_session_for_apply),
      db: DbSession = Depends(get_db_session),
  ) -> TransactionApplyResponse:
      allowed_root = Path(session.selectedFolder)
      if not allowed_root.is_dir():
          raise HTTPException(status_code=status.HTTP_410_GONE, detail="Seçili klasör artık mevcut değil")

      # Saga #309 ATDD Soru 4: apply_plan boş/sadece-LIST bir planı
      # sorunsuzca "committed" (0 FileOperation) sayar — bu, eski projenin
      # "hiçbir dosya işlenmedi ama success döndü" hata sınıfı. apply_plan
      # ÇAĞRILMADAN ÖNCE reddedilir, orchestrator.py'ye dokunulmaz.
      has_real_operation = any(step.operationType != OperationType.LIST for step in payload.plan.steps)
      if not has_real_operation:
          raise HTTPException(
              status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
              detail="Plan hiçbir gerçek dosya işlemi içermiyor",
          )

      pdf_files = discover_pdf_files(allowed_root)

      try:
          transaction = apply_plan(db, payload.plan, pdf_files, allowed_root)
      except PathWhitelistError as exc:
          logger.warning(
              "Whitelist ihlali (apply): %s %s (allowed_root=%s)",
              exc.description, exc.offending_path, exc.allowed_root,
          )
          raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{exc.description} {exc.reason}") from exc
      except PlanApplicationError as exc:
          # apply_plan zaten ATOMİK: herhangi bir adım patlarsa TÜM
          # tamamlanmış adımlar geri alınır ve transaction.status =
          # "rolled_back" olarak DB'ye yazılır (bkz. orchestrator.py).
          # Burada exception'ı 500'e çevirmek yerine, DB'de zaten
          # rolled_back olarak işaretlenmiş transaction'ı normal bir
          # 200 yanıtla döneriz — frontend'in transactionResult.ts'i
          # rolled_back'i zaten "failed" olarak gösteriyor (Saga #277).
          logger.warning("Plan uygulaması başarısız, geri alındı: %s", exc)
          # exc.__cause__ orijinal hatayı taşır ama istemciye detay
          # sızdırılmaz (dosya sistemi yapısı keşfi riski, Saga #283
          # ilkesiyle tutarlı).
          transaction = db.scalars(
              select(Transaction).order_by(Transaction.id.desc())
          ).first()
          if transaction is None:
              raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Plan uygulanamadı") from exc
          return TransactionApplyResponse(
              id=transaction.id,
              status=transaction.status,
              operations=[],
          )

      return TransactionApplyResponse(
          id=transaction.id,
          status=transaction.status,
          operations=[
              AppliedFileOperation(destination_path=op.destination_path, status=op.status)
              for op in transaction.operations
          ],
      )
  ```
  Not: `PlanApplicationError` except bloğunda "en son eklenen
  transaction'ı DB'den tekrar sorgulama" yerine DAHA TEMİZ bir yol:
  `apply_plan`in exception fırlatmadan ÖNCE oluşturduğu transaction
  nesnesine dışarıdan erişimin olmaması bir tasarım kısıtı — bu yüzden
  implementasyon subagent'ı, `PlanApplicationError.__cause__` veya
  `exc.args`e transaction id eklemenin `apply_plan`i değiştirmeyi
  gerektirdiğini fark ederse, YUKARIDAKİ "en son transaction'ı sorgula"
  yaklaşımını (test'te DB tek-thread/tek-transaction olduğu için
  güvenli) kullanmaya devam etsin — orchestrator.py'ye DOKUNULMAZ.

### Testler (backend/tests/test_main_integration.py)
- Happy path: session oluştur, gerçek bir PDF dosyası allowed_root'a
  yaz, `/api/plan` yerine DOĞRUDAN `/api/transactions/apply`e MOVE
  içeren geçerli bir `PlanSkeleton` gönder, 200 + dosyanın gerçekten
  hedef klasöre taşındığını (diskte) doğrula.
- Sıfır-işlem reddi: `steps: []` (veya tek bir `LIST` adımı) gönder,
  422 bekle, DB'de hiç `Transaction` satırı OLUŞMADIĞINI doğrula.
- Whitelist ihlali: allowed_root dışına işaret eden bir `fileNames`
  girdisi (taranan `pdf_files`de olmayan bir dosya adı) gönder, 403
  bekle.
- 404: bilinmeyen `sessionId`.
- 410: session var ama `selectedFolder` diskte yok.

## Frontend

### `ui/src/components/chat/ChatScreen.tsx`
- `ChatMessage` tipine yeni opsiyonel alan: `rawPlan?: Record<string, unknown>`
  (sadece App.tsx tarafından okunur/yazılır, ChatScreen/PlanCard bunu
  RENDER ETMEZ — mevcut render mantığına dokunulmaz).

### `ui/src/App.tsx`
- `requestPlan` içinde, `validation.plan`i `assistantMessage.plan`e
  atarken, AYRICA HAM `rawPlan` JSON'ını (validate edilmeden/budanmadan
  önceki `rawPlan` değişkeni zaten var) `assistantMessage.rawPlan`e ata.
- `handleApprovePlan(messageId)`:
  ```typescript
  async function handleApprovePlan(messageId: string) {
    if (!sessionId) return;
    const message = messages.find((m) => m.id === messageId);
    if (!message?.rawPlan) return;
    try {
      const response = await fetch(`${BACKEND_ORIGIN}/api/transactions/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId, plan: message.rawPlan }),
      });
      if (!response.ok) {
        // hata mesajı result olarak "failed" gösterilir (basit, dar kapsam)
        setMessages((current) =>
          current.map((m) => (m.id === messageId ? { ...m, result: { fileCount: 0, destinationFolders: [], status: 'failed' } } : m)),
        );
        return;
      }
      const body: BackendTransaction & { id: number } = await response.json();
      const result: TransactionResult = { ...toTransactionResult(body), transactionId: body.id };
      setMessages((current) => current.map((m) => (m.id === messageId ? { ...m, result } : m)));
    } catch {
      setMessages((current) =>
        current.map((m) => (m.id === messageId ? { ...m, result: { fileCount: 0, destinationFolders: [], status: 'failed' } } : m)),
      );
    }
  }
  ```
  `toTransactionResult`/`TransactionResult`/`BackendTransaction`
  importları eklenir (`../../lib/transactionResult` ve
  `./components/chat/ResultCard`).
- `setMessages` zaten `useState<ChatMessage[]>` — mevcut controlled
  `messages`/`onMessagesChange` deseni (Saga #287) korunur.

### Testler
- `ui/src/App.test.tsx`: bir plan mesajı üretildikten sonra "Planı
  onayla" tetiklendiğinde `fetch(/api/transactions/apply, ...)`in
  doğru body ile çağrıldığını, başarılı yanıt sonrası `ResultCard`in
  render edildiğini (data-testid="result-card") doğrulayan test(ler).
- `ui/src/lib/transactionResult.ts` DEĞİŞTİRİLMEZ (zaten yeterli).

## Dokunulmayacak dosyalar (net sınır)
- `backend/orchestrator.py` — DEĞİŞTİRİLMEZ.
- `backend/security.py` — DEĞİŞTİRİLMEZ.
- `backend/db_models.py` — DEĞİŞTİRİLMEZ.
- `ui/src/components/chat/PlanCard.tsx`, `planValidation.ts` — DEĞİŞTİRİLMEZ
  (render sözleşmesi aynı kalır, sadece App.tsx ekstra ham veri taşır).
