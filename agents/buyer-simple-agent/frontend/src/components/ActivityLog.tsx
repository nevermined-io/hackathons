import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { LogEntry } from "@/api";

const ACTION_COLORS: Record<string, string> = {
  SUCCESS: "#4ade80",
  COMPLETED: "#4ade80",
  REGISTERED: "#4ade80",
  FOUND: "#4ade80",
  RESULT: "#4ade80",
  STARTUP: "#4ade80",
  VERIFY: "#facc15",
  VERIFIED: "#facc15",
  TOKEN: "#facc15",
  PURCHASE: "#facc15",
  SETTLE: "#facc15",
  ERROR: "#f87171",
  FAILED: "#f87171",
  FETCHING: "#60a5fa",
  SENDING: "#60a5fa",
  CONNECT: "#60a5fa",
  SENT: "#60a5fa",
  RESPONSE: "#60a5fa",
  TOOL_USE: "#22d3ee",
  CHECK: "#22d3ee",
  BALANCE: "#22d3ee",
  DISCOVER: "#22d3ee",
  LIST_SELLERS: "#22d3ee",
  RECEIVED: "#c084fc",
};

interface ActivityLogProps {
  logs: LogEntry[];
}

export default function ActivityLog({ logs }: ActivityLogProps) {
  const topRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    topRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  // Show newest entries first
  const reversed = [...logs].reverse();

  return (
    <div className="flex flex-col h-full rounded-lg overflow-hidden" style={{ backgroundColor: "var(--color-log-bg)" }}>
      <div className="flex items-center gap-2 px-4 py-2 border-b border-white/10">
        <span className="font-mono text-xs font-semibold text-white/70">Activity Log</span>
        <span className="text-[10px] text-white/40 font-mono">{logs.length} entries</span>
      </div>
      <ScrollArea className="flex-1">
        <div className="px-4 py-2 space-y-0.5">
          <div ref={topRef} />
          {reversed.length === 0 && (
            <p className="font-mono text-xs text-white/30">Waiting for activity...</p>
          )}
          {reversed.map((entry, i) => {
            const actionColor = ACTION_COLORS[entry.action] ?? "#9ca3af";
            return (
              <div key={logs.length - 1 - i} className="font-mono text-[11px] leading-5 text-white/70 flex">
                <span className="text-white/30 shrink-0">{entry.timestamp}</span>
                <span className="text-white/20 mx-1.5">|</span>
                <span className="text-cyan-400/80 w-24 shrink-0 truncate">{entry.component}</span>
                <span className="text-white/20 mx-1.5">|</span>
                <span className="w-24 shrink-0 truncate font-semibold" style={{ color: actionColor }}>
                  {entry.action}
                </span>
                <span className="text-white/20 mx-1.5">|</span>
                <span className="text-white/60 truncate">{entry.message}</span>
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
