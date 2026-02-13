import { useState, useEffect, useCallback } from "react";
import {
  fetchSellers,
  fetchBalance,
  streamChat,
  connectLogStream,
  type Seller,
  type LogEntry,
  type ChatMessage,
} from "./api";
import ChatPanel from "./components/ChatPanel";
import SellerSidebar from "./components/SellerSidebar";
import ActivityLog from "./components/ActivityLog";

const MAX_LOGS = 200;

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [currentTool, setCurrentTool] = useState("");
  const [_balance, setBalance] = useState<Record<string, unknown> | null>(null);

  // Poll sellers every 5 seconds
  useEffect(() => {
    const load = () => {
      fetchSellers().then(setSellers).catch(() => {});
    };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch balance on mount
  useEffect(() => {
    fetchBalance().then((data) => {
      if (data) setBalance(data);
    });
  }, []);

  // Connect log stream (server replays history on reconnect, so deduplicate)
  useEffect(() => {
    const disconnect = connectLogStream((entry) => {
      setLogs((prev) => {
        // Deduplicate by checking if last few entries match
        const last = prev[prev.length - 1];
        if (
          last &&
          last.timestamp === entry.timestamp &&
          last.action === entry.action &&
          last.message === entry.message
        ) {
          return prev;
        }
        const next = [...prev, entry];
        return next.length > MAX_LOGS ? next.slice(-MAX_LOGS) : next;
      });
    });
    return disconnect;
  }, []);

  const handleSend = useCallback(
    async (message: string) => {
      setMessages((prev) => [...prev, { role: "user", text: message }]);
      setIsStreaming(true);
      setStreamingText("");
      setCurrentTool("");

      let lastToolUsed = "";

      await streamChat(message, {
        onToken: (text) => {
          setStreamingText((prev) => prev + text);
        },
        onToolUse: (name) => {
          setCurrentTool(name);
          lastToolUsed = name;
        },
        onDone: (fullText) => {
          setMessages((prev) => [
            ...prev,
            {
              role: "agent",
              text: fullText,
              toolUse: lastToolUsed || undefined,
            },
          ]);
          setIsStreaming(false);
          setStreamingText("");
          setCurrentTool("");
          // Refresh sellers + balance after a chat completes
          fetchSellers().then(setSellers).catch(() => {});
          fetchBalance().then((data) => {
            if (data) setBalance(data);
          });
        },
        onError: (error) => {
          setMessages((prev) => [
            ...prev,
            { role: "agent", text: `Error: ${error}` },
          ]);
          setIsStreaming(false);
          setStreamingText("");
          setCurrentTool("");
        },
      });
    },
    [],
  );

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Main content area */}
      <div className="flex flex-1 min-h-0">
        {/* Seller sidebar */}
        <div className="w-[280px] shrink-0">
          <SellerSidebar sellers={sellers} />
        </div>

        {/* Chat panel */}
        <div className="flex-1 min-w-0">
          <ChatPanel
            messages={messages}
            isStreaming={isStreaming}
            streamingText={streamingText}
            currentTool={currentTool}
            onSend={handleSend}
          />
        </div>
      </div>

      {/* Activity log */}
      <div className="h-[200px] shrink-0 border-t">
        <ActivityLog logs={logs} />
      </div>
    </div>
  );
}
