import { useState, useEffect, useRef } from 'react'
import './App.css'

const API_BASE = "http://localhost:8000";

function App() {
  const [identities, setIdentities] = useState(["primary_user", "delegate_agent"]);
  const [selectedIdentity, setSelectedIdentity] = useState("primary_user");
  const [chatMessages, setChatMessages] = useState([
    { role: "agent", text: "Hello! I am your Email Guardian assistant. How can I help you manage your inbox today?" }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [threads, setThreads] = useState([]);
  const [selectedThread, setSelectedThread] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [auditLogs, setAuditLogs] = useState([]);
  const [isBackendConnected, setIsBackendConnected] = useState(true);

  const chatEndRef = useRef(null);

  // Fetch identities on mount
  useEffect(() => {
    fetch(`${API_BASE}/identities`)
      .then(res => {
        if (!res.ok) throw new Error("Failed to load identities");
        return res.json();
      })
      .then(data => {
        setIdentities(data);
        setIsBackendConnected(true);
      })
      .catch(err => {
        console.error("Error fetching identities:", err);
        setIsBackendConnected(false);
      });
  }, []);

  // Fetch inbox threads
  const fetchInbox = () => {
    fetch(`${API_BASE}/inbox`)
      .then(res => {
        if (!res.ok) throw new Error("Failed to load inbox");
        return res.json();
      })
      .then(data => {
        setThreads(data);
        setIsBackendConnected(true);
      })
      .catch(err => {
        console.error("Error fetching inbox:", err);
        setIsBackendConnected(false);
      });
  };

  useEffect(() => {
    fetchInbox();
  }, []);

  // Fetch audit logs
  const fetchAuditLogs = () => {
    fetch(`${API_BASE}/audit-log`)
      .then(res => {
        if (!res.ok) throw new Error("Failed to load audit logs");
        return res.json();
      })
      .then(data => {
        setAuditLogs(data);
        setIsBackendConnected(true);
      })
      .catch(err => {
        console.error("Error fetching audit logs:", err);
        // Do not toggle whole backend connection on poll error to avoid flickering,
        // but still log if needed.
      });
  };

  // Poll audit log every 2 seconds
  useEffect(() => {
    fetchAuditLogs();
    const interval = setInterval(fetchAuditLogs, 2000);
    return () => clearInterval(interval);
  }, []);

  // Show a fallback message in the chat history when connection is lost
  useEffect(() => {
    if (!isBackendConnected) {
      // Avoid duplicate alerts
      const hasConnectionAlert = chatMessages.some(m => m.text.includes("Connection to the Email Guardian backend failed"));
      if (!hasConnectionAlert) {
        setChatMessages(prev => [
          ...prev,
          { 
            role: "system", 
            text: "🚨 Connection to the Email Guardian backend failed!\nPlease verify the FastAPI server is active by running:\n\nPYTHONPATH=. uv run uvicorn api.main:app --port 8000" 
          }
        ]);
      }
    }
  }, [isBackendConnected]);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isChatLoading]);

  // Handle chat submission
  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || isChatLoading) return;

    const userMsg = chatInput;
    setChatInput("");
    setChatMessages(prev => [...prev, { role: "user", text: userMsg }]);
    setIsChatLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg, identity: selectedIdentity })
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const data = await response.json();
      setChatMessages(prev => [...prev, { role: "agent", text: data.reply }]);
    } catch (err) {
      console.error("Chat error:", err);
      setChatMessages(prev => [...prev, { 
        role: "agent", 
        text: `⚠️ Error: Unable to connect to the agent. Please make sure the FastAPI server is running.` 
      }]);
      setIsBackendConnected(false);
    } finally {
      setIsChatLoading(false);
      fetchInbox();
      fetchAuditLogs();
    }
  };

  // Run Delegation Demo
  const handleDelegationDemo = async () => {
    setIsChatLoading(true);
    setChatMessages(prev => [...prev, { role: "system", text: "⚙️ Initiating Delegation Demo (3 scenarios)..." }]);
    try {
      const res = await fetch(`${API_BASE}/demo/delegation`, { method: "POST" });
      if (!res.ok) throw new Error("Delegation demo failed");
      const steps = await res.json();
      
      const newMsgs = steps.map(s => ({
        role: "system",
        text: `📍 [${s.step}]\n❓ Request: "${s.request}"\n🛡️ Decision: ${s.decision.toUpperCase()}\n📄 Reason: ${s.reason}\n🤖 Response: ${s.reply}`
      }));
      
      setChatMessages(prev => [
        ...prev, 
        ...newMsgs,
        { role: "system", text: "✅ Delegation Demo Complete. Check the Live Policy Log for real-time audit updates." }
      ]);
    } catch (err) {
      console.error(err);
      setChatMessages(prev => [...prev, { role: "system", text: "❌ Error executing delegation demo. Is the API server running?" }]);
      setIsBackendConnected(false);
    } finally {
      setIsChatLoading(false);
      fetchInbox();
      fetchAuditLogs();
    }
  };

  // Run Scope-Drift Demo
  const handleScopeDriftDemo = async () => {
    setIsChatLoading(true);
    setChatMessages(prev => [...prev, { role: "system", text: "⚙️ Initiating Scope-Drift Demo..." }]);
    try {
      const res = await fetch(`${API_BASE}/demo/scope-drift`, { method: "POST" });
      if (!res.ok) throw new Error("Scope-drift demo failed");
      const data = await res.json();
      
      setChatMessages(prev => [
        ...prev,
        {
          role: "system",
          text: `📍 [Scope-Drift Protection]\n❓ Request: "${data.request}"\n🔍 Discovery: ${data.discovery}\n⚠️ Blocked Target: ${data.blocked_part}\n🛡️ Decision: ${data.decision.toUpperCase()}\n📄 Reason: ${data.reason}\n🤖 Response: ${data.reply}`
        },
        { role: "system", text: "✅ Scope-Drift Demo Complete. Check the Live Policy Log for real-time audit updates." }
      ]);
    } catch (err) {
      console.error(err);
      setChatMessages(prev => [...prev, { role: "system", text: "❌ Error executing scope-drift demo. Is the API server running?" }]);
      setIsBackendConnected(false);
    } finally {
      setIsChatLoading(false);
      fetchInbox();
      fetchAuditLogs();
    }
  };

  // Click thread to show details
  const handleThreadClick = async (threadId) => {
    try {
      const res = await fetch(`${API_BASE}/inbox/${threadId}`);
      if (!res.ok) throw new Error("Failed to load thread details");
      const data = await res.json();
      setSelectedThread(data);
      setIsModalOpen(true);
    } catch (err) {
      console.error("Error fetching thread:", err);
    }
  };

  // Helper to format timestamp
  const formatTime = (isoString) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="app-container">
      {!isBackendConnected && (
        <div className="connection-error-banner">
          ⚠️ Connection to backend failed! Please ensure the FastAPI server is running on <strong>http://localhost:8000</strong>.
        </div>
      )}
      
      <header className="app-header">
        <div className="header-brand">
          <div className="logo-shield">🛡️</div>
          <div className="title-area">
            <h1>Email Guardian</h1>
            <span className="badge">Policy-Enforced Agent</span>
          </div>
        </div>
        <div className="header-actions">
          <div className="demo-controls">
            <button onClick={handleDelegationDemo} className="demo-btn delegation-btn" disabled={isChatLoading}>
              Run Delegation Demo
            </button>
            <button onClick={handleScopeDriftDemo} className="demo-btn scope-drift-btn" disabled={isChatLoading}>
              Run Scope-Drift Demo
            </button>
          </div>
          <div className="identity-control">
            <label htmlFor="identity-select">Role:</label>
            <select 
              id="identity-select" 
              value={selectedIdentity} 
              onChange={(e) => setSelectedIdentity(e.target.value)}
              className="identity-dropdown"
              disabled={!isBackendConnected}
            >
              {identities.map(id => (
                <option key={id} value={id}>{id}</option>
              ))}
            </select>
          </div>
        </div>
      </header>

      <main className="panel-container">
        {/* LEFT PANEL: CHAT CO-PILOT */}
        <section className="panel chat-panel" aria-label="Guardian Assistant Chat">
          <div className="panel-header">
            <h2>💬 Copilot Assistant</h2>
            {isChatLoading && <span className="pulsing-loader-text">Agent is thinking...</span>}
          </div>
          <div className="chat-messages-container">
            {chatMessages.map((msg, idx) => (
              <div key={idx} className={`chat-message ${msg.role}`}>
                {msg.role !== 'system' && (
                  <div className="message-sender">
                    {msg.role === 'user' ? 'You' : 'Guardian Agent'}
                  </div>
                )}
                <div className="message-bubble">
                  {msg.text}
                </div>
              </div>
            ))}
            {isChatLoading && (
              <div className="chat-message agent loading">
                <div className="message-sender">Guardian Agent</div>
                <div className="message-bubble">
                  <span className="dot"></span>
                  <span className="dot"></span>
                  <span className="dot"></span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          <form onSubmit={handleChatSubmit} className="chat-input-form">
            <input 
              type="text" 
              placeholder="Tell the agent what to do (e.g., summarize, reply, send)..." 
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              className="chat-input-field"
              disabled={isChatLoading || !isBackendConnected}
            />
            <button type="submit" className="chat-send-btn" disabled={isChatLoading || !chatInput.trim() || !isBackendConnected}>
              Send
            </button>
          </form>
        </section>

        {/* CENTER PANEL: EMAIL INBOX */}
        <section className="panel inbox-panel" aria-label="Mock Email Inbox">
          <div className="panel-header">
            <h2>📥 Email Inbox</h2>
            <button onClick={fetchInbox} className="refresh-btn" title="Refresh Inbox" disabled={!isBackendConnected}>
              🔄 Refresh
            </button>
          </div>
          <div className="threads-list">
            {!isBackendConnected ? (
              <div className="empty-inbox">Backend unreachable. Seed threads cannot be retrieved.</div>
            ) : threads.length === 0 ? (
              <div className="empty-inbox">No threads in the inbox.</div>
            ) : (
              threads.map((thread) => {
                const isUrgent = thread.last_message_preview?.toLowerCase().includes("urgent") || 
                                 thread.subject?.toLowerCase().includes("overdue") || 
                                 thread.subject?.toLowerCase().includes("security");
                return (
                  <div 
                    key={thread.id} 
                    className={`thread-item ${isUrgent ? 'urgent' : ''}`}
                    onClick={() => handleThreadClick(thread.id)}
                  >
                    <div className="thread-meta">
                      <span className="thread-id">Thread #{thread.id}</span>
                      {isUrgent && <span className="urgent-badge">URGENT</span>}
                    </div>
                    <h3 className="thread-subject">{thread.subject}</h3>
                    <div className="thread-participants">
                      <strong>From:</strong> {thread.participants.join(", ")}
                    </div>
                    <p className="thread-preview">{thread.last_message_preview}</p>
                  </div>
                );
              })
            )}
          </div>
        </section>

        {/* RIGHT PANEL: LIVE POLICY AUDIT LOG */}
        <section className="panel audit-panel" aria-label="Live Policy Log">
          <div className="panel-header">
            <h2>📜 Live Policy Log</h2>
            <div className="live-status">
              <span className="live-pulse"></span>
              <span className="live-text">LIVE</span>
            </div>
          </div>
          <div className="logs-list">
            {!isBackendConnected ? (
              <div className="empty-logs">Backend unreachable. Logs cannot be retrieved.</div>
            ) : auditLogs.length === 0 ? (
              <div className="empty-logs">No policy decisions logged yet.</div>
            ) : (
              auditLogs.map((log) => (
                <div 
                  key={log.id} 
                  className={`log-item ${log.decision === 'allow' ? 'allowed' : 'blocked'}`}
                >
                  <div className="log-meta">
                    <span className="log-time">{formatTime(log.timestamp)}</span>
                    <span className="log-identity">@{log.identity}</span>
                    <span className={`log-decision-badge ${log.decision}`}>{log.decision.toUpperCase()}</span>
                  </div>
                  <div className="log-action">
                    <strong>Action:</strong> <code>{log.action}</code>
                  </div>
                  <div className="log-params">
                    <strong>Params:</strong> <code>{JSON.stringify(log.params)}</code>
                  </div>
                  <p className="log-reason">{log.reason}</p>
                </div>
              ))
            )}
          </div>
        </section>
      </main>

      {/* DETAILED THREAD DIALOG OVERLAY */}
      {isModalOpen && selectedThread && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>{selectedThread.subject}</h2>
                <div className="modal-participants">
                  <strong>Participants:</strong> {selectedThread.participants.join(", ")}
                </div>
              </div>
              <button className="close-btn" onClick={() => setIsModalOpen(false)}>✖</button>
            </div>
            <div className="modal-body">
              <div className="messages-list">
                {selectedThread.messages.map((msg) => (
                  <div key={msg.id} className={`email-msg ${msg.sender === 'me@company.com' ? 'sent' : 'received'} ${msg.is_urgent ? 'urgent' : ''}`}>
                    <div className="msg-header">
                      <span className="msg-sender">{msg.sender}</span>
                      <span className="msg-time">{new Date(msg.timestamp).toLocaleString()}</span>
                    </div>
                    <div className="msg-recipients">
                      <strong>To:</strong> {msg.to_field} {msg.cc && <span>| <strong>CC:</strong> {msg.cc}</span>}
                    </div>
                    <div className="msg-body">
                      {msg.body}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
