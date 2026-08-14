import * as React from "react"

import { cn } from "@/lib/utils"

/**
 * Styled native <select>. The app keeps platform selects (reliable on phones,
 * zero JS) but dresses them in the same tokens and focus conventions as the
 * generated shadcn controls.
 */
function NativeSelect({
  className,
  ...props
}: React.ComponentProps<"select">) {
  return (
    <select
      data-slot="native-select"
      className={cn(
        "h-9 rounded-lg border border-input bg-panel-raised px-3 text-sm font-medium text-foreground transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { NativeSelect }
