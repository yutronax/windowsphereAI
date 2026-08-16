import { useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';

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
  const isPathTooltipVisible = isFocused || isHovered;
  const isReady = backendStatus === 'ready';

  async function chooseFolder() {
    const folder = await open({ directory: true, multiple: false });
    if (typeof folder === 'string') setSelectedFolder(folder);
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
      `}</style>
      <button type="button" className="onboarding-primary-btn" onClick={chooseFolder} disabled={!isReady}>Klasör Seç</button>
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
          >
            {selectedFolder}
          </p>
          {isPathTooltipVisible && (
            <span id="folder-path-tooltip-content" role="tooltip" data-testid="folder-path-tooltip">{selectedFolder}</span>
          )}
        </>
      )}
      <textarea
        data-testid="request-textarea"
        aria-label="Dosya işlemi isteği"
        className="onboarding-textarea"
        value={requestText}
        onChange={(e) => setRequestText(e.target.value)}
      />
      <button type="button" onClick={onContinue} disabled={!isReady || !selectedFolder}>Devam</button>
    </main>
  );
}
