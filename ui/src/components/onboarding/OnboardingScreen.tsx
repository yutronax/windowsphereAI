import { useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';

type BackendStatus = 'ready' | 'starting' | 'backend_timeout';

type Props = {
  backendStatus: BackendStatus;
  onContinue: () => void;
  onRetry?: () => void;
};

export function truncateWindowsPath(path: string, maxLength: number): string {
  if (path.length <= maxLength) return path;

  const lastSeparator = path.lastIndexOf('\\');
  const finalFolder = lastSeparator >= 0 ? path.slice(lastSeparator) : path;
  const prefixLength = maxLength - finalFolder.length - 1;

  if (prefixLength <= 0) return `…${finalFolder.slice(-(maxLength - 1))}`;
  return `${path.slice(0, prefixLength)}…${finalFolder}`;
}

export default function OnboardingScreen({ backendStatus, onContinue, onRetry }: Props) {
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
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
      <button type="button" onClick={chooseFolder} disabled={!isReady}>Klasör Seç</button>
      {selectedFolder && <p data-testid="selected-folder-path" title={selectedFolder}>{truncateWindowsPath(selectedFolder, 80)}</p>}
      <button type="button" onClick={onContinue} disabled={!isReady || !selectedFolder}>Devam</button>
    </main>
  );
}
