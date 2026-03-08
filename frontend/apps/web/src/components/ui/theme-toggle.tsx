"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return (
    <input
      type="checkbox"
      role="switch"
      className="theme-checkbox"
      checked={theme === "dark"}
      onChange={(e) => setTheme(e.target.checked ? "dark" : "light")}
      aria-label="Toggle dark mode"
    />
  );
}
