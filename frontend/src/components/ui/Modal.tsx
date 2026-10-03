import { useEffect, type ReactNode } from "react";

// Shared pop-up for "click a summary tile for the detail" (used across Overview, Plant and
// Equipment pages so those pages themselves can stay a single, non-scrolling screen). Esc and
// a backdrop click both close it.
export function Modal({
  title,
  onClose,
  children,
  wide,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-ink/30 p-4" onClick={onClose}>
      <div
        className={`flex max-h-[85vh] w-full flex-col border border-line bg-paper shadow-popover ${
          wide ? "max-w-[960px]" : "max-w-[560px]"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-line px-2 py-1.5">
          <span className="text-12 font-semibold uppercase tracking-wide text-mute">{title}</span>
          <button type="button" onClick={onClose} className="text-13 text-mute hover:text-ink">
            Close
          </button>
        </div>
        <div className="overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
