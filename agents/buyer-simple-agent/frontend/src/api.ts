export interface Seller {
  url: string;
  name: string;
  description: string;
  skills: string[];
  credits: number;
  cost_description: string;
}

export interface LogEntry {
  timestamp: string;
  component: string;
  action: string;
  message: string;
}

export interface ChatMessage {
  role: "user" | "agent";
  text: string;
  toolUse?: string;
}

export async function fetchSellers(): Promise<Seller[]> {
  const res = await fetch("/api/sellers");
  if (!res.ok) return [];
  return res.json();
}

export async function fetchBalance(): Promise<{
  balance: Record<string, unknown>;
  budget: Record<string, unknown>;
} | null> {
  try {
    const res = await fetch("/api/balance");
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export interface StreamCallbacks {
  onToken: (text: string) => void;
  onToolUse: (name: string) => void;
  onDone: (fullText: string) => void;
  onError: (message: string) => void;
}

export async function streamChat(
  message: string,
  callbacks: StreamCallbacks,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    callbacks.onError(`HTTP ${res.status}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    callbacks.onError("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const dataStr = line.slice(5).trim();
        if (!dataStr) continue;
        try {
          const data = JSON.parse(dataStr);
          switch (currentEvent) {
            case "token":
              callbacks.onToken(data.text);
              break;
            case "tool_use":
              callbacks.onToolUse(data.name);
              break;
            case "done":
              callbacks.onDone(data.text);
              break;
            case "error":
              callbacks.onError(data.error);
              break;
          }
        } catch {
          // Skip malformed JSON
        }
      }
    }
  }
}

export function connectLogStream(
  onLog: (entry: LogEntry) => void,
): () => void {
  const es = new EventSource("/api/logs/stream");

  es.addEventListener("log", (e) => {
    try {
      const entry: LogEntry = JSON.parse(e.data);
      onLog(entry);
    } catch {
      // Skip malformed entries
    }
  });

  es.addEventListener("error", () => {
    // EventSource auto-reconnects
  });

  return () => es.close();
}
