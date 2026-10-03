import type { ReactNode } from "react";
import { useAppState } from "../../state/AppStateContext";
import { formatMoneyKusd } from "../../lib/format";

// SPEC section 5.11: Executive sees all money; Plant manager only for their picked plant;
// Engineer sees no money values ("impact shown as tons, hours and priority labels" instead,
// via the `fallback` prop at each call site). Where no fallback applies, the figure is erased
// entirely rather than replaced with a "hidden" placeholder: a role that can't see a number
// shouldn't see a label for it either.
export function Money({
  kusd,
  plantCode,
  fallback,
}: {
  kusd: number | null | undefined;
  plantCode?: string | null;
  fallback?: ReactNode;
}) {
  const { canSeeMoney } = useAppState();

  if (kusd == null) return <span className="text-mute">-</span>;
  if (canSeeMoney(plantCode)) return <>{formatMoneyKusd(kusd)}</>;
  return <>{fallback ?? null}</>;
}
