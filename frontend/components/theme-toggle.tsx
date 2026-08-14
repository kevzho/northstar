"use client";

/**
 * Dark/light switch. next-themes owns the html class and persistence. The
 * mounted check goes through useSyncExternalStore (server snapshot false,
 * client snapshot true) so server and client HTML agree without the
 * setState-in-effect pattern the project's lint rejects.
 */

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

const emptySubscribe = () => () => {};

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );

  const isLight = mounted && resolvedTheme === "light";

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={isLight ? "Switch to dark mode" : "Switch to light mode"}
      onClick={() => setTheme(isLight ? "dark" : "light")}
    >
      {isLight ? <Moon aria-hidden /> : <Sun aria-hidden />}
    </Button>
  );
}
