"use client";

import { useEffect, useState } from "react";

import { MoonIcon, SunIcon } from "@/components/icons";

export function ThemeToggle() {
  const [light, setLight] = useState(false);

  // The no-flash script in layout.tsx sets the class before paint; mirror it into state.
  useEffect(() => {
    setLight(document.documentElement.classList.contains("light"));
  }, []);

  const toggle = () => {
    const next = !light;
    setLight(next);
    document.documentElement.classList.toggle("light", next);
    try {
      localStorage.setItem("praxis-theme", next ? "light" : "dark");
    } catch {
      /* storage unavailable — fall back to in-memory only */
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      title={light ? "Switch to dark" : "Switch to light"}
      aria-label="Toggle theme"
      className="grid h-8 w-8 place-items-center rounded-lg border border-white/10 text-ink-faint transition-colors hover:text-ink"
    >
      {light ? <MoonIcon width={15} height={15} /> : <SunIcon width={15} height={15} />}
    </button>
  );
}
