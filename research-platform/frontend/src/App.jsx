import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const STORAGE_KEY = "research_chat_history";
const MAX_SESSIONS = 20;

const getMessageId = () => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const formatStatusContent = (status, report) => {
  if (status === "DONE") {
    return report || "No report generated.";
  }

  if (status === "FAILED") {
    return report || "Research failed.";
  }

  if (!status || status === "RUNNING") {
    return "Researching...";
  }

  return `${status}...`;
};

const createSession = (messages = [], title = "New chat") => ({
  id: getMessageId(),
  title,
  timestamp: new Date().toISOString(),
  messages,
});

const sortSessions = (sessionList) =>
  [...sessionList].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  );

const formatTimestamp = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
};

export default function App() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [eventSource, setEventSource] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    try {
      const storedValue = localStorage.getItem(STORAGE_KEY);
      if (storedValue) {
        const parsed = JSON.parse(storedValue);
        if (Array.isArray(parsed) && parsed.length) {
          const normalized = sortSessions(
            parsed
              .filter((session) => session && typeof session === "object")
              .map((session) => ({
                ...session,
                title: session.title || "New chat",
                messages: session.messages || [],
              })),
          ).slice(0, MAX_SESSIONS);

          if (normalized.length) {
            setSessions(normalized);
            setActiveSessionId(normalized[0].id);
            setMessages(normalized[0].messages || []);
            return;
          }
        }
      }
    } catch {
      // Fall back to a fresh session when storage data is invalid.
    }

    const initialSession = createSession([], "New chat");
    setSessions([initialSession]);
    setActiveSessionId(initialSession.id);
    setMessages([]);
  }, []);

  useEffect(() => {
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [eventSource]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!sessions.length) {
      localStorage.removeItem(STORAGE_KEY);
      return;
    }

    const normalized = sortSessions(sessions)
      .slice(0, MAX_SESSIONS)
      .map((session) => ({
        ...session,
        messages: session.messages || [],
      }));

    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
  }, [sessions]);

  const appendMessage = (message) => {
    setMessages((prev) => {
      const nextMessages = [...prev, message];
      setSessions((currentSessions) =>
        sortSessions(
          currentSessions.map((session) =>
            session.id === activeSessionId
              ? { ...session, messages: nextMessages }
              : session,
          ),
        ),
      );
      return nextMessages;
    });
  };

  const createFreshSession = () => {
    const freshSession = createSession([], "New chat");
    setSessions((prev) => sortSessions([freshSession, ...prev]));
    setActiveSessionId(freshSession.id);
    setMessages([]);
    setError("");
    setLoading(false);
    setQuery("");

    if (eventSource) {
      eventSource.close();
      setEventSource(null);
    }
  };

  const selectSession = (sessionId) => {
    const selectedSession = sessions.find((session) => session.id === sessionId);
    if (!selectedSession) {
      return;
    }

    setActiveSessionId(sessionId);
    setMessages(selectedSession.messages || []);
    setError("");
    setLoading(false);
    setQuery("");

    if (eventSource) {
      eventSource.close();
      setEventSource(null);
    }
  };

  async function submitQuery() {
    if (!query.trim() || loading) {
      return;
    }

    setError("");

    const trimmedQuery = query.trim();
    const userMessage = {
      id: getMessageId(),
      role: "user",
      content: trimmedQuery,
    };

    const assistantId = getMessageId();
    const assistantMessage = {
      id: assistantId,
      role: "assistant",
      content: "Researching...",
      status: "running",
    };

    const nextMessages = [...messages, userMessage, assistantMessage];
    setMessages(nextMessages);
    setSessions((currentSessions) =>
      sortSessions(
        currentSessions.map((session) =>
          session.id === activeSessionId
            ? {
                ...session,
                title: trimmedQuery.slice(0, 40),
                timestamp: new Date().toISOString(),
                messages: nextMessages,
              }
            : session,
        ),
      ),
    );
    setLoading(true);
    setQuery("");

    if (eventSource) {
      eventSource.close();
    }

    const res = await fetch("http://localhost:8000/research", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer demo-token",
      },
      body: JSON.stringify({ query: userMessage.content }),
    });

    if (!res.ok) {
      setError("Research request failed");
      setLoading(false);
      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                content: "Research request failed.",
                status: "failed",
              }
            : message,
        ),
      );
      return;
    }

    const { task_id } = await res.json();
    connectStream(task_id, assistantId);
  }

  function connectStream(taskId, assistantId) {
    const source = new EventSource(`http://localhost:8002/stream/${taskId}`);

    source.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const newContent = formatStatusContent(data.status, data.report);
      const newStatus =
        data.status === "DONE"
          ? "done"
          : data.status === "FAILED"
            ? "failed"
            : "running";

      setMessages((prev) => {
        const updatedMessages = prev.map((message) =>
          message.id === assistantId
            ? { ...message, content: newContent, status: newStatus }
            : message,
        );

        setSessions((currentSessions) =>
          sortSessions(
            currentSessions.map((session) =>
              session.id === activeSessionId
                ? { ...session, messages: updatedMessages }
                : session,
            ),
          ),
        );

        return updatedMessages;
      });

      if (data.status === "FAILED") {
        setError(data.report || "Research failed.");
        setLoading(false);
        source.close();
      }

      if (data.status === "DONE") {
        setLoading(false);
        source.close();
      }
    };

    source.onerror = () => {
      setError("Stream disconnected");
      setLoading(false);
      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantId
            ? { ...message, content: "Stream disconnected.", status: "failed" }
            : message,
        ),
      );
      source.close();
    };

    setEventSource(source);
  }

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitQuery();
    }
  };

  return (
    <div className={`app-shell ${isSidebarOpen ? "" : "sidebar-collapsed"}`}>
      <div className="chat-sidebar">
        <button className="sidebar-new-chat" onClick={createFreshSession}>
          + New Chat
        </button>

        <div className="sidebar-session-list">
          {sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <button
                key={session.id}
                className={`sidebar-session-button ${isActive ? "active" : ""}`}
                onClick={() => selectSession(session.id)}
              >
                <div className="session-title">{session.title}</div>
                <div className="session-meta">
                  {formatTimestamp(session.timestamp)}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="main-panel">
        <header className="main-panel-header">
          <div>
            <button
              className="sidebar-toggle"
              onClick={() => setIsSidebarOpen((prev) => !prev)}
              aria-label="Toggle sidebar"
            >
              ☰
            </button>
            <h1>🔍 Research Platform</h1>
            <p>
              Ask questions and get live research reports in chat form.
            </p>
          </div>
        </header>

        <div className="chat-messages">
          {messages.map((message) => {
            const isUser = message.role === "user";
            const isAssistant = message.role === "assistant";
            return (
              <div
                key={message.id}
                className={`chat-message-row ${isUser ? "user" : "assistant"}`}
              >
                <div className={`chat-bubble ${isUser ? "user" : "assistant"}`}>
                  {isAssistant && message.status === "running" ? (
                    <div className="assistant-running">
                      <span>{message.content}</span>
                      <span className="typing-dots" aria-hidden="true">
                        <span>•</span>
                        <span>•</span>
                        <span>•</span>
                      </span>
                    </div>
                  ) : message.status === "failed" ? (
                    <div className="assistant-error">{message.content}</div>
                  ) : isAssistant ? (
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  ) : (
                    <div>{message.content}</div>
                  )}
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        <div className="composer-card">
          {error && <div className="composer-error">{error}</div>}

          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your question..."
            rows={1}
            disabled={loading}
            className="composer-input"
          />

          <div className="composer-actions">
            <button
              onClick={submitQuery}
              disabled={loading || !query.trim()}
              className={`composer-button ${loading ? "loading" : ""}`}
            >
              {loading ? "Researching…" : "Run Research"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
