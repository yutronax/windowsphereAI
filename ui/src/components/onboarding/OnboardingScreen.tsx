import { useRef, useState, type KeyboardEvent } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { invoke } from '@tauri-apps/api/core';

type BackendStatus = 'ready' | 'starting' | 'backend_timeout';

type Props = {
  backendStatus: BackendStatus;
  onContinue: () => void;
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
  const latestRequestedPathRef = useRef<string | null>(null);
  const chooseFolderButtonRef = useRef<HTMLButtonElement>(null);
  const requestTextareaRef = useRef<HTMLTextAreaElement>(null);
  const isPathTooltipVisible = isFocused || isHovered;
  const isReady = backendStatus === 'ready';
  const canSubmit = isReady && !!selectedFolder && !isFolderInvalid && !isValidatingFolder;

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

  function handleContinueClick() {
    if (!canSubmit) return;
    if (requestText.trim() === '') {
      setIsRequestEmpty(true);
      requestTextareaRef.current?.focus();
      return;
    }
    onContinue();
  }

  function handleFolderPathKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter') handleContinueClick();
  }

  return (
    <main>
      <h1>Klasör Seç</h1>
      {backendStatus === 'starting' && <p>Başlatılıyor…</p>}
      {backendStatus === 'backend_timeout' && (
        <>
          <p>Backend ulaşılamadı veya zaman aşımına uğradı.</p>
          <button type="button" onClick={onRetry}>Tekrar dene</button>
        </>
      )}
      <style>{`
        .onboarding-primary-btn {
          height: 44px;
          border-radius: 8px;
          background-color: #2563EB;
          color: #fff;
          border: none;
        }
        .onboarding-primary-btn:hover:not(:disabled) {
          background-color: #1D4ED8;
        }
        .onboarding-primary-btn:active:not(:disabled) {
          background-color: #1E40AF;
        }
        .onboarding-primary-btn:focus-visible {
          outline: 2px solid #1E40AF;
          outline-offset: 2px;
        }
        .onboarding-primary-btn:disabled {
          background-color: #94A3B8;
          cursor: not-allowed;
        }
        .onboarding-path {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 320px;
        }
        .onboarding-textarea {
          width: 100%;
          box-sizing: border-box;
          min-height: 120px;
          border-radius: 12px;
          border: 1px solid #E5E7EB;
          font-size: 16px;
          padding: 16px;
        }
        .onboarding-textarea:focus {
          border-color: #2563EB;
          box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
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
          margin-top: 4px;
        }
      `}</style>
      <button ref={chooseFolderButtonRef} type="button" className="onboarding-primary-btn" onClick={chooseFolder} disabled={!isReady}>Klasör Seç</button>
      {selectedFolder && (
        <>
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
      <button type="button" onClick={handleContinueClick} disabled={!canSubmit}>Devam</button>
    </main>
  );
}
