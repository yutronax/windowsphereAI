// Merkezi design token dosyası (Saga #345, Epic #36).
// Kaynak: task #347 envanteri — OnboardingScreen, ChatScreen, PlanCard,
// ResultCard, TransactionHistoryPanel bileşenlerinde tekrarlanan inline
// stil değerleri. Bu dosya henüz hiçbir bileşen tarafından import edilmiyor
// (taşıma işi ayrı task'larda, bkz. Saga #346).

export const tokens = {
  colors: {
    primary: '#1E3A8A',
    primaryHover: '#1E3172',
    primaryActive: '#172554',
    border: '#E5E7EB',
    danger: '#DC2626',
    textSecondary: '#4B5563',
    textMuted: '#6B7280',
    textDark: '#111827',
    panelBackground: '#F3F4F6',
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
