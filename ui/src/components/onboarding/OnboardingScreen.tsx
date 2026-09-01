import { useRef, useState, type KeyboardEvent } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { invoke } from '@tauri-apps/api/core';
import { BACKEND_ORIGIN } from '../../lib/backendHealth';

type BackendStatus = 'ready' | 'starting' | 'backend_timeout';

type Props = {
  backendStatus: BackendStatus;
  onContinue: (sessionId: string) => void;
  onRetry?: () => void;
};

export default function OnboardingScreen({ backendStatus, onContinue, onRetry }: Props) {
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [requestText, setRequestText] = useState('');
  const [isRequestEmpty, setIsRequestEmpty] = useState(false);
  const [isFolderInvalid, setIsFolderInvalid] = useState(false);
  const [isValidatingFolder, setIsValidatingFolder] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const latestRequestedPathRef = useRef<string | null>(null);
  const chooseFolderButtonRef = useRef<HTMLButtonElement>(null);
  const requestTextareaRef = useRef<HTMLTextAreaElement>(null);
  const isPathTooltipVisible = isFocused || isHovered;
  const isReady = backendStatus === 'ready';
  const canSubmit = isReady && !!selectedFolder && !isFolderInvalid && !isValidatingFolder && !isSubmitting;

  async function chooseFolder() {
    const folder = await open({ directory: true, multiple: false });
    if (typeof folder !== 'string') return;

    const normalizedPath = folder.replace(/[\\/]+$/, '');
    latestRequestedPathRef.current = normalizedPath;
    setSelectedFolder(normalizedPath);
    setIsFolderInvalid(false);
    setIsValidatingFolder(true);

    let isAccessible: boolean;
    try {
      isAccessible = await invoke<boolean>('plugin:fs|exists', { path: normalizedPath });
    } catch {
      isAccessible = false;
    }

    if (latestRequestedPathRef.current !== normalizedPath) return;
    setIsFolderInvalid(!isAccessible);
    setIsValidatingFolder(false);
    if (!isAccessible) chooseFolderButtonRef.current?.focus();
  }

  function handleRequestTextChange(value: string) {
    setRequestText(value);
    if (isRequestEmpty && value.trim() !== '') setIsRequestEmpty(false);
  }

  async function handleContinueClick() {
    if (!canSubmit) return;
    if (requestText.trim() === '') {
      setIsRequestEmpty(true);
      requestTextareaRef.current?.focus();
      return;
    }

    setSubmitError(null);
    setIsSubmitting(true);
    try {
      const response = await fetch(`${BACKEND_ORIGIN}/api/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selectedFolder, requestText }),
      });
      if (!response.ok) throw new Error('session request failed');
      const session: { sessionId: string } = await response.json();
      setIsSubmitting(false);
      onContinue(session.sessionId);
    } catch {
      setIsSubmitting(false);
      setSubmitError('İstek gönderilemedi. Lütfen tekrar deneyin.');
    }
  }

  function handleFolderPathKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter') handleContinueClick();
  }

  return (
    <main data-testid="onboarding-card" className="onboarding-card">
      <h1>Klasör Seç</h1>
      <p className="onboarding-subtitle">Hangi klasördeki dosyaları organize etmek istersiniz?</p>
      {backendStatus === 'starting' && (
        <div data-testid="backend-status-banner" className="backend-status-banner" role="status">
          <p>Başlatılıyor…</p>
        </div>
      )}
      {backendStatus === 'backend_timeout' && (
        <div data-testid="backend-status-banner" className="backend-status-banner" role="status">
          <p>Backend ulaşılamadı veya zaman aşımına uğradı.</p>
          <button type="button" onClick={onRetry}>Tekrar dene</button>
        </div>
      )}
      <style>{`
        main.onboarding-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          padding: 32px 16px;
          background-color: #f5f5f5;
          box-sizing: border-box;
          max-width: 560px;
          margin: 0 auto;
          width: 100%;
        }
        .onboarding-card > h1 {
          font-size: 32px;
          font-weight: 700;
          margin: 0 0 8px 0;
          text-align: center;
        }
        .onboarding-card > .onboarding-subtitle {
          font-size: 16px;
          color: #6B7280;
          text-align: center;
          margin: 0 0 32px 0;
        }
        .backend-status-banner {
          background-color: #fef3c7;
          border: 1px solid #fcd34d;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 24px;
        }
        .backend-status-banner p {
          margin: 0 0 12px 0;
          color: #92400e;
          font-size: 14px;
        }
        .backend-status-banner button {
          background-color: #92400e;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 8px 16px;
          cursor: pointer;
          font-size: 14px;
        }
        .backend-status-banner button:hover {
          background-color: #78350f;
        }
        .onboarding-primary-btn {
          height: 44px;
          border-radius: 8px;
          background-color: #1E3A8A;
          color: #fff;
          border: none;
          font-size: 16px;
          font-weight: 500;
          cursor: pointer;
          margin-bottom: 16px;
        }
        .onboarding-primary-btn:hover:not(:disabled) {
          background-color: #1E3172;
        }
        .onboarding-primary-btn:active:not(:disabled) {
          background-color: #172554;
        }
        .onboarding-primary-btn:focus-visible {
          outline: 2px solid #1E3A8A;
          outline-offset: 2px;
        }
        .onboarding-primary-btn:disabled {
          background-color: #94A3B8;
          cursor: not-allowed;
        }
        .onboarding-path-wrapper {
          background-color: #f3f4f6;
          border-radius: 6px;
          padding: 12px 16px;
          margin-bottom: 16px;
        }
        .onboarding-path {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          margin: 0;
          font-size: 14px;
          color: #374151;
        }
        .onboarding-textarea {
          width: 100%;
          box-sizing: border-box;
          min-height: 120px;
          border-radius: 8px;
          border: 1px solid #E5E7EB;
          font-size: 16px;
          padding: 16px;
          font-family: inherit;
          margin-bottom: 16px;
        }
        .onboarding-textarea:focus {
          border-color: #1E3A8A;
          box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.1);
          outline: none;
        }
        .onboarding-textarea::placeholder {
          color: #9CA3AF;
        }
        .onboarding-textarea.has-error {
          border-color: #DC2626;
        }
        .onboarding-textarea.has-error:focus {
          border-color: #DC2626;
          box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
        }
        .onboarding-error-message {
          color: #DC2626;
          font-size: 14px;
          margin: 0 0 16px 0;
        }
        .onboarding-continue-btn {
          width: 100%;
          height: 44px;
          border-radius: 8px;
          background-color: #1E3A8A;
          color: #fff;
          border: none;
          font-size: 16px;
          font-weight: 500;
          cursor: pointer;
        }
        .onboarding-continue-btn:hover:not(:disabled) {
          background-color: #1E3172;
        }
        .onboarding-continue-btn:active:not(:disabled) {
          background-color: #172554;
        }
        .onboarding-continue-btn:focus-visible {
          outline: 2px solid #1E3A8A;
          outline-offset: 2px;
        }
        .onboarding-continue-btn:disabled {
          background-color: #94A3B8;
          cursor: not-allowed;
        }
      `}</style>
      <button ref={chooseFolderButtonRef} type="button" className="onboarding-primary-btn" onClick={chooseFolder} disabled={!isReady}>Klasör Seç</button>
      {selectedFolder && (
        <>
          <div className="onboarding-path-wrapper">
            <p
              data-testid="selected-folder-path"
              className="onboarding-path"
              tabIndex={0}
              aria-describedby="folder-path-tooltip-content"
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
              onKeyDown={handleFolderPathKeyDown}
            >
              {selectedFolder}
            </p>
          </div>
          {isPathTooltipVisible && (
            <span id="folder-path-tooltip-content" role="tooltip" data-testid="folder-path-tooltip">{selectedFolder}</span>
          )}
        </>
      )}
      {isFolderInvalid && (
        <div aria-live="polite">
          <p className="onboarding-error-message">Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin.</p>
        </div>
      )}
      <textarea
        ref={requestTextareaRef}
        data-testid="request-textarea"
        aria-label="Dosya işlemi isteği"
        className={isRequestEmpty ? 'onboarding-textarea has-error' : 'onboarding-textarea'}
        placeholder="Bu klasördeki PDF'leri tarihe göre sırala"
        value={requestText}
        onChange={(e) => handleRequestTextChange(e.target.value)}
      />
      {isRequestEmpty && (
        <div aria-live="polite">
          <p className="onboarding-error-message">Devam etmek için bir istek yazın.</p>
        </div>
      )}
      {submitError && (
        <div aria-live="polite">
          <p className="onboarding-error-message">{submitError}</p>
        </div>
      )}
      <button type="button" className="onboarding-continue-btn" onClick={handleContinueClick} disabled={!canSubmit}>Devam</button>
    </main>
  );
}
