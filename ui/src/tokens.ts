// Merkezi design token dosyası (Saga #345, Epic #36).
// Kaynak: task #347 envanteri — OnboardingScreen, ChatScreen, PlanCard,
// ResultCard, TransactionHistoryPanel bileşenlerinde tekrarlanan inline
// stil değerleri. Bu dosya henüz hiçbir bileşen tarafından import edilmiyor
// (taşıma işi ayrı task'larda, bkz. Saga #346).

export const tokens = {
  colors: {
    primary: 'var(--color-primary)',
    primaryHover: 'var(--color-primary-hover)',
    primaryActive: 'var(--color-primary-active)',
    border: 'var(--color-border)',
    danger: 'var(--color-danger)',
    textSecondary: 'var(--color-text-secondary)',
    textMuted: 'var(--color-text-muted)',
    textDark: 'var(--color-text-dark)',
    panelBackground: 'var(--color-panel-background)',
    dangerBannerBg: 'var(--color-danger-banner-bg)',
    dangerBannerBorder: 'var(--color-danger-banner-border)',
    dangerBannerText: 'var(--color-danger-banner-text)',
    dangerMessageBg: 'var(--color-danger-message-bg)',
    dangerMessageBorder: 'var(--color-danger-message-border)',
    dangerMessageText: 'var(--color-danger-message-text)',
    successBg: 'var(--color-success-bg)',
    successBorder: 'var(--color-success-border)',
    successText: 'var(--color-success-text)',
    connected: 'var(--color-connected)',
    white: 'var(--color-white)',
  },
  radius: {
    default: '8px',
  },
  size: {
    buttonHeight: '44px',
  },
  fontSize: {
    small: '14px',
    base: '16px',
  },
  spacing: {
    buttonPadding: '0 20px',
  },
} as const;
