'use client';

import { createContext, useContext, useEffect, useState } from 'react';

const DEFAULT_THEME = 'dark';
const STORAGE_KEY = 'ant_theme_mode';

const ThemeContext = createContext({ theme: DEFAULT_THEME, toggleTheme: () => {} });

// The <html> class is also set synchronously by an inline script in app/layout.jsx
// (before hydration) to avoid a flash of the wrong theme - this effect just brings
// React state in sync with whatever that script already applied.
export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(DEFAULT_THEME);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    const initial = stored === 'light' || stored === 'dark' ? stored : DEFAULT_THEME;
    setThemeState(initial);
    document.documentElement.classList.toggle('dark', initial === 'dark');
  }, []);

  const setTheme = (next) => {
    if (next !== 'light' && next !== 'dark') return;
    setThemeState(next);
    localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.classList.toggle('dark', next === 'dark');
  };

  const toggleTheme = () => setTheme(theme === 'dark' ? 'light' : 'dark');

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
