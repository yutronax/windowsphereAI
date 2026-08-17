import { useEffect, useState } from 'react';
import OnboardingScreen from './components/onboarding/OnboardingScreen';
import { waitForBackendHealth } from './lib/backendHealth';

type SetupConfig = { selectedFolder: string };

export default function App() {
  const [config, setConfig] = useState<SetupConfig | null | undefined>(undefined);
  const [backendStatus, setBackendStatus] = useState<'ready' | 'starting' | 'backend_timeout'>('starting');
  const [sessionId, setSessionId] = useState<string | null>(null);

  function checkBackend() {
    setBackendStatus('starting');
    void waitForBackendHealth().then(({ status }) => setBackendStatus(status));
  }

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/config')
      .then((response) => (response.ok ? response.json() : null))
      .then((value) => setConfig(value))
      .catch(() => setConfig(null));
    checkBackend();
  }, []);

  if (config === undefined) return null;
  if (config || sessionId) return <main data-testid="main-chat-screen">Ana sohbet ekranı</main>;

  return <OnboardingScreen backendStatus={backendStatus} onContinue={setSessionId} onRetry={checkBackend} />;
}
