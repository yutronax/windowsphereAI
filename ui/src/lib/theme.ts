// Saga #360: Dark/light theme persistence and toggling

export function applyStoredTheme(): void {
  try {
    const storedTheme = localStorage.getItem('theme');
    if (storedTheme === 'light') {
      document.documentElement.dataset.theme = 'light';
    }
  } catch {
    // Silently default to dark theme if localStorage is inaccessible
  }
}

export function toggleTheme(): void {
  const currentTheme = getTheme();
  try {
    if (currentTheme === 'dark') {
      document.documentElement.dataset.theme = 'light';
      localStorage.setItem('theme', 'light');
    } else {
      delete document.documentElement.dataset.theme;
      localStorage.setItem('theme', 'dark');
    }
  } catch {
    // DOM is still updated even if localStorage fails
    if (currentTheme === 'dark') {
      document.documentElement.dataset.theme = 'light';
    } else {
      delete document.documentElement.dataset.theme;
    }
  }
}

export function getTheme(): 'light' | 'dark' {
  return document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
}
