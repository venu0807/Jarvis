'use client';
import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'upskill' | 'analytics' | 'proposals'>('chat');
  
  const [data, setData] = useState<any>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [lesson, setLesson] = useState<string>('');
  const [alerts, setAlerts] = useState<any[]>([]);
  const [automations, setAutomations] = useState<any[]>([]);
  const [newTask, setNewTask] = useState('');
  const [generatingId, setGeneratingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedFix, setCopiedFix] = useState(false);
  
  const [chatMessages, setChatMessages] = useState<{role: string, content: string}[]>([
    { role: 'assistant', content: 'Hello Venu. I am Hermes. I have access to your bots and your long-term memory. How can I help you today?' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    const fetchAllData = async () => {
      try {
        const [statsRes, analyticsRes, lessonRes, alertsRes, autoRes] = await Promise.all([
          fetch('/api/stats'),
          fetch('/api/analytics'),
          fetch('/api/lesson'),
          fetch('/api/alerts'),
          fetch('/api/automations')
        ]);
        
        setData(await statsRes.json());
        
        const analyticsJson = await analyticsRes.json();
        if (!analyticsJson.error) setAnalytics(analyticsJson);
        
        const lessonJson = await lessonRes.json();
        setLesson(lessonJson.content || '');
        
        const alertsJson = await alertsRes.json();
        if (Array.isArray(alertsJson)) setAlerts(alertsJson);

        const autoJson = await autoRes.json();
        if (autoJson.tasks) setAutomations(autoJson.tasks);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setChatLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userMessage })
      });
      const json = await res.json();
      
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: json.response || json.error || 'Failed to get response.' 
      }]);
    } catch (e) {
      setChatMessages(prev => [...prev, { role: 'assistant', content: '⚠️ Neural Link Disconnected.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleFixAlerts = async () => {
    try {
      const errorMsg = alerts.map(a => `${a.job}: ${a.message}`).join(', ');
      const prompt = `Act as my Debugger. Investigate why these automations failed in Jarvis: ${errorMsg}`;
      await navigator.clipboard.writeText(prompt);
      setCopiedFix(true);
      setTimeout(() => setCopiedFix(false), 3000);
    } catch (e) {
      console.error('Failed to copy', e);
    }
  };

  const handleClearAlerts = async () => {
    try {
      await fetch('/api/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'clear' })
      });
      setAlerts([]);
    } catch (e) {
      console.error('Failed to clear alerts', e);
    }
  };

  const handleTaskSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTask.trim()) return;
    try {
      await fetch('/api/automations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_description: newTask })
      });
      setNewTask('');
      const res = await fetch('/api/automations');
      const json = await res.json();
      if (json.tasks) setAutomations(json.tasks);
    } catch (e) {
      console.error('Failed to submit task', e);
    }
  };

  const handleGenerateCode = async (id: number, task_description: string) => {
    setGeneratingId(id);
    try {
      await fetch('/api/automations/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, task_description })
      });
      const res = await fetch('/api/automations');
      const json = await res.json();
      if (json.tasks) setAutomations(json.tasks);
    } catch (e) {
      console.error(e);
    } finally {
      setGeneratingId(null);
    }
  };

  const handleDeploy = async (id: number, proposed_code: string) => {
    try {
      await fetch('/api/automations/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, proposed_code })
      });
      const res = await fetch('/api/automations');
      const json = await res.json();
      if (json.tasks) setAutomations(json.tasks);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <main className="dashboard-container">
      <header className="header">
        <h1>JARVIS OS</h1>
        <div className="status-badge">
          <div className="status-dot"></div>
          {loading ? 'SYNCING...' : 'ONLINE'}
        </div>
      </header>

      {alerts.length > 0 && (
        <div className="alert-banner" style={{ background: 'rgba(255, 0, 0, 0.2)', border: '1px solid #ff4444', color: '#ffaaaa', padding: '1rem', margin: '0 2rem 1rem', borderRadius: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <strong>⚠️ CRITICAL AUTOMATION FAILURE DETECTED:</strong>
            <ul style={{ margin: '0.5rem 0 0 1.5rem' }}>
              {alerts.map((alert, i) => (
                <li key={i}>{alert.job} failed at {new Date(alert.time).toLocaleTimeString()} - {alert.message}</li>
              ))}
            </ul>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button onClick={handleFixAlerts} style={{ background: '#45a29e', color: '#0b0c10', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
              {copiedFix ? 'Copied Prompt!' : '🔧 Fix Issue'}
            </button>
            <button onClick={handleClearAlerts} style={{ background: '#ff4444', color: '#fff', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
              Acknowledge & Clear
            </button>
          </div>
        </div>
      )}

      <div className="layout-grid">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="panel">
            <h2>System Status</h2>
            <div className="status-item">✅ Master Daemon Running</div>
            <div className="status-item">✅ Event Bus Online</div>
            
            <hr className="divider" />
            
            <div className="sidebar-metric">📌 Pinterest Posts: {data?.metrics?.pinterest || 0}</div>
            <div className="sidebar-metric">💼 Jobs Auto-Applied: {data?.metrics?.jobsAuto || 0}</div>
            <div className="sidebar-metric">🧠 Memories Stored: {data?.metrics?.memories || 0}</div>
            
            <hr className="divider" />
            
            <h3>🌅 Morning Briefing</h3>
            <div className="briefing-box">
              {data?.briefing || "Loading briefing..."}
            </div>
            
            <hr className="divider" />
            
            <h3>📥 Automate-My-Life Inbox</h3>
            <form onSubmit={handleTaskSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <input 
                type="text" 
                value={newTask}
                onChange={(e) => setNewTask(e.target.value)}
                placeholder="What manual chore should I automate?" 
                style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #45a29e', background: '#1f2833', color: '#fff' }}
              />
              <button type="submit" style={{ background: '#45a29e', color: '#0b0c10', border: 'none', padding: '0.5rem', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                Submit Request
              </button>
            </form>
          </div>
        </aside>

        {/* Main Content Area */}
        <section className="main-content">
          <div className="tabs">
            <button className={`tab ${activeTab === 'chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>💬 Chat</button>
            <button className={`tab ${activeTab === 'upskill' ? 'active' : ''}`} onClick={() => setActiveTab('upskill')}>🧠 Daily Upskill</button>
            <button className={`tab ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>📈 Analytics</button>
            <button className={`tab ${activeTab === 'proposals' ? 'active' : ''}`} onClick={() => setActiveTab('proposals')}>⚡ Automation Proposals</button>
          </div>

          <div className="tab-content">
            {activeTab === 'chat' && (
              <div className="panel chat-panel">
                <div className="chat-messages">
                  {chatMessages.map((msg, i) => (
                    <div key={i} className={`chat-message ${msg.role === 'user' ? 'user-message' : 'bot-message'}`}>
                      <div className="message-content">{msg.content}</div>
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="chat-message bot-message">
                      <div className="message-content loading-dots">Thinking<span>.</span><span>.</span><span>.</span></div>
                    </div>
                  )}
                </div>
                <form onSubmit={handleChatSubmit} className="chat-input-form">
                  <input 
                    type="text" 
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask Jarvis..." 
                    className="chat-input"
                    disabled={chatLoading}
                  />
                  <button type="submit" className="chat-submit" disabled={chatLoading}>
                    Send
                  </button>
                </form>
              </div>
            )}

            {activeTab === 'upskill' && (
              <div className="panel upskill-panel markdown-body">
                {lesson ? <ReactMarkdown>{lesson}</ReactMarkdown> : <p>Loading lesson...</p>}
              </div>
            )}

            {activeTab === 'analytics' && (
              <div className="panel analytics-panel">
                <h2>Total Automation Events</h2>
                <div className="analytics-summary">
                  {analytics?.categories?.map((cat: any, i: number) => (
                    <div key={i} className="analytics-card">
                      <div className="analytics-label">{cat.category.replace('_', ' ')}</div>
                      <div className="analytics-val">{cat.total}</div>
                    </div>
                  ))}
                  {!analytics?.categories?.length && <p>No metrics logged yet.</p>}
                </div>
                
                {analytics?.breakdown?.length > 0 && (
                  <div className="chart-container" style={{ height: '300px', marginTop: '2rem' }}>
                    <h3>Event Breakdown</h3>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.breakdown} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                        <XAxis dataKey="name" stroke="#c5c6c7" fontSize={12} />
                        <YAxis stroke="#c5c6c7" fontSize={12} />
                        <Tooltip contentStyle={{ backgroundColor: '#1f2833', border: '1px solid #45a29e' }} />
                        <Bar dataKey="total" fill="#66fcf1" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'proposals' && (
              <div className="panel proposals-panel">
                <h2>⚡ Pending Automation Proposals</h2>
                {automations.length === 0 ? (
                  <p>No automation requests found. Submit a chore in the sidebar inbox!</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {automations.map(task => (
                      <div key={task.id} style={{ border: '1px solid #45a29e', borderRadius: '8px', padding: '1rem', background: '#1f2833' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                          <h3 style={{ margin: 0 }}>[{task.status.toUpperCase()}] {task.task_description}</h3>
                          <small style={{ color: '#c5c6c7' }}>{new Date(task.created_at).toLocaleString()}</small>
                        </div>
                        
                        {task.status === 'pending' && (
                          <div>
                            <p style={{ color: '#c5c6c7' }}>Hermes is ready to analyze this request and write the code.</p>
                            <button 
                              onClick={() => handleGenerateCode(task.id, task.task_description)}
                              disabled={generatingId === task.id}
                              style={{ background: '#45a29e', color: '#0b0c10', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: generatingId === task.id ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}
                            >
                              {generatingId === task.id ? 'Thinking...' : 'Generate Code via Hermes'}
                            </button>
                          </div>
                        )}

                        {task.status === 'draft' && (
                          <div>
                            <p style={{ color: '#c5c6c7' }}>### 🤖 Hermes Proposed Code</p>
                            <pre style={{ background: '#0b0c10', padding: '1rem', borderRadius: '4px', overflowX: 'auto', border: '1px solid #333' }}>
                              <code style={{ color: '#66fcf1' }}>{task.proposed_code}</code>
                            </pre>
                            <button 
                              onClick={() => handleDeploy(task.id, task.proposed_code)}
                              style={{ background: '#66fcf1', color: '#0b0c10', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', marginTop: '1rem' }}
                            >
                              ✅ Approve & Deploy
                            </button>
                          </div>
                        )}

                        {task.status === 'deployed' && (
                          <div>
                            <p style={{ color: '#45a29e', fontWeight: 'bold' }}>✅ This automation has been deployed.</p>
                            <details>
                              <summary style={{ cursor: 'pointer', color: '#c5c6c7', marginTop: '0.5rem' }}>View Deployed Code</summary>
                              <pre style={{ background: '#0b0c10', padding: '1rem', borderRadius: '4px', overflowX: 'auto', border: '1px solid #333', marginTop: '0.5rem' }}>
                                <code style={{ color: '#66fcf1' }}>{task.proposed_code}</code>
                              </pre>
                            </details>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
