'use client';
import { useEffect, useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#66fcf1', '#45a29e', '#f2a900', '#50c878', '#ff4444'];

export default function Home() {
  // 4 Core Master Tabs + Chat
  const [activeTab, setActiveTab] = useState<'job-tracker' | 'interview-prep' | 'outreach' | 'upskill' | 'chat'>('job-tracker');
  
  // Data States
  const [data, setData] = useState<any>(null);
  const [jobStats, setJobStats] = useState<any>(null);
  const [outreachData, setOutreachData] = useState<any>(null);
  const [lesson, setLesson] = useState<string>('');
  const [alerts, setAlerts] = useState<any[]>([]);
  
  // Job Tracker State (4 Portals)
  const [jobsList, setJobsList] = useState<any[]>([]);
  const [jobSearch, setJobSearch] = useState('');
  const [portalFilter, setPortalFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [selectedJob, setSelectedJob] = useState<any>(null);
  const [prepData, setPrepData] = useState<{ [key: string]: string }>({});
  const [prepLoading, setPrepLoading] = useState<string | null>(null);

  // Manual Job Add Modal State
  const [showAddJobModal, setShowAddJobModal] = useState(false);
  const [manualUrl, setManualUrl] = useState('');
  const [manualCompany, setManualCompany] = useState('');
  const [manualTitle, setManualTitle] = useState('');
  const [manualLocation, setManualLocation] = useState('');
  const [manualPortal, setManualPortal] = useState('Manual Apply');
  const [manualDesc, setManualDesc] = useState('');
  const [isFetchingUrl, setIsFetchingUrl] = useState(false);
  const [isSavingManualJob, setIsSavingManualJob] = useState(false);
  const [fetchNotice, setFetchNotice] = useState('');

  // Interview Prep State
  const [interviewsList, setInterviewsList] = useState<any[]>([]);
  const [interviewSearch, setInterviewSearch] = useState('');
  const [selectedInterview, setSelectedInterview] = useState<any>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newCompany, setNewCompany] = useState('');
  const [newRole, setNewRole] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [isCreatingPrep, setIsCreatingPrep] = useState(false);

  // Chat State
  const [inputMessage, setInputMessage] = useState('');
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([
    { role: 'assistant', content: "Hello Venu, I am Jarvis (Hermes). All 4 job portals (Naukri, Indeed, Internshala, Foundit), interview bots, and outreach engines are running smoothly. How can I help you?" }
  ]);
  const [isLoading, setIsLoading] = useState(false);

  // Initial Fast Parallel Fetch
  useEffect(() => {
    async function loadAllData() {
      try {
        const [statsRes, lessonRes, alertsRes, jobsRes, jobStatsRes, outreachRes, interviewsRes] = await Promise.all([
          fetch('/api/stats'),
          fetch('/api/lesson'),
          fetch('/api/alerts'),
          fetch('/api/jobs'),
          fetch('/api/jobstats'),
          fetch('/api/outreach'),
          fetch('/api/interviews')
        ]);
        
        const [statsJson, lessonJson, alertsJson, jobsJson, jobStatsJson, outreachJson, interviewsJson] = await Promise.all([
          statsRes.json().catch(() => ({})),
          lessonRes.json().catch(() => ({})),
          alertsRes.json().catch(() => ({})),
          jobsRes.json().catch(() => ({})),
          jobStatsRes.json().catch(() => ({})),
          outreachRes.json().catch(() => ({})),
          interviewsRes.json().catch(() => ({}))
        ]);

        if (statsJson && !statsJson.error) setData(statsJson);
        if (lessonJson && !lessonJson.error) setLesson(lessonJson.content || '');
        if (alertsJson && !alertsJson.error) setAlerts(alertsJson.alerts || []);
        if (jobsJson && jobsJson.jobs) {
          setJobsList(jobsJson.jobs);
          if (jobsJson.jobs.length > 0) setSelectedJob(jobsJson.jobs[0]);
        }
        if (jobStatsJson && !jobStatsJson.error) setJobStats(jobStatsJson);
        if (outreachJson && !outreachJson.error) setOutreachData(outreachJson);
        if (interviewsJson && interviewsJson.interviews) {
          setInterviewsList(interviewsJson.interviews);
          if (interviewsJson.interviews.length > 0) setSelectedInterview(interviewsJson.interviews[0]);
        }
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      }
    }
    loadAllData();
  }, []);

  // Quick 4-Portal + Manual Counts
  const portalCounts = useMemo(() => {
    const counts: { [key: string]: number } = { All: jobsList.length, Naukri: 0, Indeed: 0, Internshala: 0, Foundit: 0, Manual: 0 };
    jobsList.forEach(j => {
      const p = (j.portal || '').toLowerCase();
      const isManual = p.includes('manual') || (j.id && String(j.id).startsWith('manual_')) || p.includes('direct');
      if (isManual) counts.Manual++;
      if (p.includes('naukri')) counts.Naukri++;
      else if (p.includes('indeed')) counts.Indeed++;
      else if (p.includes('internshala')) counts.Internshala++;
      else if (p.includes('foundit') || p.includes('monster')) counts.Foundit++;
    });
    return counts;
  }, [jobsList]);

  // Filtered Jobs across 4 Portals + Manual
  const filteredJobs = useMemo(() => {
    return jobsList.filter(job => {
      const p = (job.portal || '').toLowerCase();
      const isManual = p.includes('manual') || (job.id && String(job.id).startsWith('manual_')) || p.includes('direct');
      const matchesPortal = 
        portalFilter === 'All' ? true :
        portalFilter === 'Manual' ? isManual :
        portalFilter === 'Naukri' ? p.includes('naukri') :
        portalFilter === 'Indeed' ? p.includes('indeed') :
        portalFilter === 'Internshala' ? p.includes('internshala') :
        portalFilter === 'Foundit' ? (p.includes('foundit') || p.includes('monster')) : true;

      const matchesStatus = statusFilter === 'All' || job.status === statusFilter;
      const matchesSearch = !jobSearch.trim() ||
        (job.title || '').toLowerCase().includes(jobSearch.toLowerCase()) ||
        (job.company || '').toLowerCase().includes(jobSearch.toLowerCase()) ||
        (job.location || '').toLowerCase().includes(jobSearch.toLowerCase());

      return matchesPortal && matchesStatus && matchesSearch;
    });
  }, [jobsList, portalFilter, statusFilter, jobSearch]);

  // CSV Export Function
  const handleExportCSV = () => {
    if (filteredJobs.length === 0) return;
    const headers = ['Company', 'Job Title', 'Portal', 'Location', 'Status', 'Applied Date', 'URL'];
    const rows = filteredJobs.map(j => [
      `"${(j.company || '').replace(/"/g, '""')}"`,
      `"${(j.title || '').replace(/"/g, '""')}"`,
      `"${(j.portal || '').replace(/"/g, '""')}"`,
      `"${(j.location || '').replace(/"/g, '""')}"`,
      `"${(j.status || 'applied').replace(/"/g, '""')}"`,
      `"${(j.timestamp ? new Date(j.timestamp).toLocaleDateString() : '')}"`,
      `"${(j.url || '').replace(/"/g, '""')}"`
    ]);
    
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    const dateStr = new Date().toISOString().split('T')[0];
    link.setAttribute('download', `applied_jobs_${portalFilter.toLowerCase()}_${dateStr}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Auto-Fetch Details from URL
  const handleFetchJobFromUrl = async () => {
    if (!manualUrl.trim()) return;
    setIsFetchingUrl(true);
    setFetchNotice('');
    try {
      const res = await fetch('/api/jobs/manual-add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'fetch', url: manualUrl.trim() })
      });
      const json = await res.json();
      if (json.success) {
        if (json.company) setManualCompany(json.company);
        if (json.title) setManualTitle(json.title);
        if (json.location) setManualLocation(json.location);
        if (json.portal) setManualPortal(json.portal);
        if (json.description) setManualDesc(json.description);
        if (json.note) setFetchNotice(json.note);
      }
    } catch (e) {
      console.error('Fetch URL error:', e);
      setFetchNotice('Error connecting to scraper. Please enter details manually.');
    } finally {
      setIsFetchingUrl(false);
    }
  };

  // Save Manual Job to Database
  const handleSaveManualJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualCompany.trim() || !manualTitle.trim()) return;
    setIsSavingManualJob(true);
    try {
      const res = await fetch('/api/jobs/manual-add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'save',
          url: manualUrl.trim(),
          company: manualCompany.trim(),
          title: manualTitle.trim(),
          location: manualLocation.trim() || 'Remote / India',
          portal: manualPortal.trim() || 'Manual Apply',
          description: manualDesc.trim()
        })
      });
      const json = await res.json();
      if (json.success && json.job) {
        setJobsList(prev => [json.job, ...prev]);
        setSelectedJob(json.job);
        setShowAddJobModal(false);
        // Reset form
        setManualUrl('');
        setManualCompany('');
        setManualTitle('');
        setManualLocation('');
        setManualPortal('Manual Apply');
        setManualDesc('');
        setFetchNotice('');
      }
    } catch (e) {
      console.error('Save manual job error:', e);
    } finally {
      setIsSavingManualJob(false);
    }
  };

  // Filtered Interviews
  const filteredInterviews = useMemo(() => {
    return interviewsList.filter(item => {
      if (!interviewSearch.trim()) return true;
      const s = interviewSearch.toLowerCase();
      return (item.company || '').toLowerCase().includes(s) ||
             (item.title || '').toLowerCase().includes(s) ||
             (item.content || '').toLowerCase().includes(s);
    });
  }, [interviewsList, interviewSearch]);

  const handleGeneratePrep = async (job: any) => {
    if (!job) return;
    setPrepLoading(job.id);
    try {
      const res = await fetch('/api/jobs/prep', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company: job.company, title: job.title, description: job.description })
      });
      const json = await res.json();
      if (json.prep) {
        setPrepData(prev => ({ ...prev, [job.id]: json.prep }));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setPrepLoading(null);
    }
  };

  const handleRegenerateInterview = async (interview: any) => {
    if (!interview) return;
    setIsRegenerating(true);
    try {
      const res = await fetch('/api/interviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company: interview.company,
          title: interview.title,
          description: `Role: ${interview.title} at ${interview.company}`
        })
      });
      const json = await res.json();
      if (json.content) {
        const updated = { ...interview, content: json.content, updated_at: new Date().toISOString() };
        setSelectedInterview(updated);
        setInterviewsList(prev => prev.map(item => item.id === interview.id ? updated : item));
      }
    } catch (e) {
      console.error('Error regenerating prep:', e);
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleCreateNewPrep = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCompany.trim()) return;
    setIsCreatingPrep(true);
    try {
      const res = await fetch('/api/interviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company: newCompany,
          title: newRole || 'Developer',
          description: newDesc
        })
      });
      const json = await res.json();
      if (json.content) {
        const newObj = {
          id: (json.file || newCompany).replace('.md', ''),
          company: newCompany,
          title: newRole || 'Developer',
          location: 'Direct',
          portal: 'Manual / Direct',
          url: '',
          applied_at: new Date().toISOString().split('T')[0],
          updated_at: new Date().toISOString(),
          content: json.content,
          has_calendar: false,
          calendar_file: ''
        };
        setInterviewsList(prev => [newObj, ...prev]);
        setSelectedInterview(newObj);
        setShowAddModal(false);
        setNewCompany('');
        setNewRole('');
        setNewDesc('');
      }
    } catch (e) {
      console.error('Create prep error:', e);
    } finally {
      setIsCreatingPrep(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    const userMsg = inputMessage;
    setInputMessage('');
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userMsg })
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response || "No response received." }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: "Error connecting to Jarvis core engine." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="dashboard-container" style={{ maxWidth: '1440px', margin: '0 auto', padding: '1rem' }}>
      {/* Top Header */}
      <header className="header" style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="logo-area" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="status-indicator" style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#50c878', boxShadow: '0 0 8px #50c878' }}></div>
          <h1 style={{ margin: 0, fontSize: '1.4rem', color: '#66fcf1', letterSpacing: '1px' }}>JARVIS COMMAND CENTER</h1>
          <span style={{ fontSize: '0.75rem', background: '#1f2833', color: '#45a29e', padding: '2px 8px', borderRadius: '4px', border: '1px solid #45a29e' }}>v3.6-ACCURATE</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ fontSize: '0.85rem', color: '#c5c6c7' }}>OPERATOR: <strong style={{ color: '#fff' }}>VENU (Fresher • MCA 2026)</strong></span>
          <span style={{ fontSize: '0.75rem', background: '#50c87822', color: '#50c878', padding: '3px 8px', borderRadius: '4px', border: '1px solid #50c878' }}>● ALL 4 PORTALS + MANUAL ACTIVE</span>
        </div>
      </header>

      {/* 4 Quick Stat Cards */}
      <section className="kpi-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.25rem' }}>
        <div 
          className="kpi-card" 
          onClick={() => setActiveTab('job-tracker')}
          style={{ cursor: 'pointer', borderLeft: '4px solid #66fcf1', transition: 'all 0.2s' }}
        >
          <div className="kpi-title" style={{ fontSize: '0.8rem', color: '#c5c6c7' }}>TOTAL APPLIED (4 PORTALS + MANUAL)</div>
          <div className="kpi-value" style={{ fontSize: '2rem', fontWeight: 'bold', color: '#66fcf1', margin: '4px 0' }}>
            {data?.jobs_applied ?? jobsList.length}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#888' }}>
            Naukri: {portalCounts.Naukri} • Indeed: {portalCounts.Indeed} • Internshala: {portalCounts.Internshala} • Foundit: {portalCounts.Foundit} • Manual: <span style={{ color: '#bd93f9', fontWeight: 'bold' }}>{portalCounts.Manual}</span>
          </div>
        </div>

        <div 
          className="kpi-card" 
          onClick={() => setActiveTab('interview-prep')}
          style={{ cursor: 'pointer', borderLeft: '4px solid #50c878', transition: 'all 0.2s', background: activeTab === 'interview-prep' ? '#1f2833' : undefined }}
        >
          <div className="kpi-title" style={{ fontSize: '0.8rem', color: '#c5c6c7' }}>INTERVIEWS & ASSESSMENTS</div>
          <div className="kpi-value" style={{ fontSize: '2rem', fontWeight: 'bold', color: '#50c878', margin: '4px 0' }}>
            {interviewsList.length}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#50c878' }}>
            Uncodemy, NxtWave + AI Cheat Sheets Ready
          </div>
        </div>

        <div 
          className="kpi-card" 
          onClick={() => setActiveTab('outreach')}
          style={{ cursor: 'pointer', borderLeft: '4px solid #f2a900', transition: 'all 0.2s' }}
        >
          <div className="kpi-title" style={{ fontSize: '0.8rem', color: '#c5c6c7' }}>OUTREACH & NETWORKING</div>
          <div className="kpi-value" style={{ fontSize: '2rem', fontWeight: 'bold', color: '#f2a900', margin: '4px 0' }}>
            {outreachData?.stats?.totalSent ?? 40}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#888' }}>
            {outreachData?.stats?.totalReplies ?? 0} Replies • {outreachData?.stats?.pendingFollowups ?? 0} Pending Follow-ups
          </div>
        </div>

        <div 
          className="kpi-card" 
          onClick={() => setActiveTab('upskill')}
          style={{ cursor: 'pointer', borderLeft: '4px solid #45a29e', transition: 'all 0.2s' }}
        >
          <div className="kpi-title" style={{ fontSize: '0.8rem', color: '#c5c6c7' }}>DAILY UPSKILL & CRASH COURSE</div>
          <div className="kpi-value" style={{ fontSize: '2rem', fontWeight: 'bold', color: '#fff', margin: '4px 0' }}>
            {lesson ? '1 Ready' : 'Synced'}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#45a29e' }}>
            High-Impact Technical Mentorship Active
          </div>
        </div>
      </section>

      {/* Main Navigation Tabs */}
      <div className="tabs-header" style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #1f2833', marginBottom: '1rem', paddingBottom: '0.5rem' }}>
        <button 
          className={`tab ${activeTab === 'job-tracker' ? 'active' : ''}`} 
          onClick={() => setActiveTab('job-tracker')}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem' }}
        >
          💼 4-Portal + Manual Job Tracker
          <span style={{ background: '#66fcf122', color: '#66fcf1', padding: '2px 8px', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 'bold' }}>
            {jobsList.length}
          </span>
        </button>

        <button 
          className={`tab ${activeTab === 'interview-prep' ? 'active' : ''}`} 
          onClick={() => setActiveTab('interview-prep')}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem' }}
        >
          🎯 Interview Prep & Notes
          {interviewsList.length > 0 && (
            <span style={{ background: '#50c878', color: '#0b0c10', padding: '2px 8px', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 'bold' }}>
              {interviewsList.length}
            </span>
          )}
        </button>

        <button 
          className={`tab ${activeTab === 'outreach' ? 'active' : ''}`} 
          onClick={() => setActiveTab('outreach')}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem' }}
        >
          📬 Outreach
        </button>

        <button 
          className={`tab ${activeTab === 'upskill' ? 'active' : ''}`} 
          onClick={() => setActiveTab('upskill')}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem' }}
        >
          🧠 Daily Upskill
        </button>

        <button 
          className={`tab ${activeTab === 'chat' ? 'active' : ''}`} 
          onClick={() => setActiveTab('chat')}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem', marginLeft: 'auto' }}
        >
          💬 Jarvis Assistant
        </button>
      </div>

      {/* Main Tab Content View */}
      <div className="tab-content">
        
        {/* ======================================================== */}
        {/* 1. 💼 4-PORTAL + MANUAL JOB TRACKER (FAST & ACCURATE) */}
        {/* ======================================================== */}
        {activeTab === 'job-tracker' && (
          <div className="panel" style={{ height: '720px', display: 'flex', flexDirection: 'column' }}>
            {/* Quick 4-Portal + Manual Filter Chips + Manual Job Add + Export CSV */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.85rem', color: '#c5c6c7', marginRight: '4px' }}>Portals:</span>
                {[
                  { name: 'All', label: `All (${portalCounts.All})`, color: '#66fcf1' },
                  { name: 'Naukri', label: `Naukri (${portalCounts.Naukri})`, color: '#45a29e' },
                  { name: 'Indeed', label: `Indeed (${portalCounts.Indeed})`, color: '#50c878' },
                  { name: 'Internshala', label: `Internshala (${portalCounts.Internshala})`, color: '#f2a900' },
                  { name: 'Foundit', label: `Foundit (${portalCounts.Foundit})`, color: '#ff79c6' },
                  { name: 'Manual', label: `Manual (${portalCounts.Manual})`, color: '#bd93f9' },
                ].map(p => (
                  <button
                    key={p.name}
                    onClick={() => setPortalFilter(p.name)}
                    style={{
                      background: portalFilter === p.name ? p.color : '#1f2833',
                      color: portalFilter === p.name ? '#0b0c10' : '#c5c6c7',
                      border: `1px solid ${p.color}`,
                      padding: '4px 12px',
                      borderRadius: '16px',
                      fontSize: '0.8rem',
                      fontWeight: 'bold',
                      cursor: 'pointer',
                      transition: 'all 0.15s'
                    }}
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              {/* Action Buttons: Add Job by URL + Status + Search + Export CSV */}
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <button
                  onClick={() => setShowAddJobModal(true)}
                  style={{
                    background: 'linear-gradient(135deg, #66fcf1, #45a29e)',
                    color: '#0b0c10',
                    border: 'none',
                    padding: '6px 14px',
                    borderRadius: '6px',
                    fontSize: '0.85rem',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  🔗 + Add Job by URL
                </button>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  style={{ background: '#1f2833', border: '1px solid #45a29e', color: '#fff', padding: '6px 10px', borderRadius: '6px', fontSize: '0.85rem' }}
                >
                  <option value="All">All Statuses</option>
                  <option value="applied">Applied</option>
                  <option value="interview">Interview</option>
                  <option value="rejected">Rejected</option>
                </select>

                <input
                  type="text"
                  placeholder="🔍 Search jobs..."
                  value={jobSearch}
                  onChange={(e) => setJobSearch(e.target.value)}
                  style={{ width: '180px', background: '#1f2833', border: '1px solid #45a29e', color: '#fff', padding: '6px 12px', borderRadius: '6px', fontSize: '0.85rem' }}
                />

                <button
                  onClick={handleExportCSV}
                  title="Download all filtered applications as CSV"
                  style={{
                    background: 'rgba(102, 252, 241, 0.15)',
                    color: '#66fcf1',
                    border: '1px solid #66fcf1',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    fontSize: '0.85rem',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  📥 Export CSV
                </button>
              </div>
            </div>

            {/* Split List & Detail Layout */}
            <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '1rem', flex: 1, minHeight: 0 }}>
              {/* Job List */}
              <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem', paddingRight: '4px' }}>
                {filteredJobs.length === 0 ? (
                  <div style={{ textAlign: 'center', color: '#888', padding: '3rem 1rem' }}>No jobs match current portal or search filter.</div>
                ) : (
                  filteredJobs.map((job) => {
                    const isSelected = selectedJob?.id === job.id;
                    const statusColor = job.status === 'interview' ? '#50c878' : job.status === 'rejected' ? '#ff4444' : '#66fcf1';
                    return (
                      <div
                        key={job.id}
                        onClick={() => setSelectedJob(job)}
                        style={{
                          padding: '0.75rem',
                          background: isSelected ? '#1f2833' : '#0b0c10',
                          border: `1px solid ${isSelected ? '#66fcf1' : '#1f2833'}`,
                          borderRadius: '6px',
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.25rem',
                          transition: 'all 0.15s'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <strong style={{ color: '#fff', fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '240px' }}>
                            {job.title}
                          </strong>
                          <span style={{ fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px', background: `${statusColor}22`, color: statusColor, fontWeight: 'bold' }}>
                            {(job.status || 'APPLIED').toUpperCase()}
                          </span>
                        </div>
                        <div style={{ color: '#c5c6c7', fontSize: '0.8rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {job.company} • {job.location}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#888' }}>
                          <span style={{ color: '#45a29e' }}>{job.portal}</span>
                          <span>{job.timestamp ? new Date(job.timestamp).toLocaleDateString() : '—'}</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Job Detail Panel */}
              <div style={{ background: '#1f2833', padding: '1.25rem', borderRadius: '6px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {selectedJob ? (
                  <>
                    <div style={{ borderBottom: '1px solid #45a29e33', paddingBottom: '0.75rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <h2 style={{ margin: 0, color: '#66fcf1', fontSize: '1.3rem' }}>{selectedJob.title}</h2>
                        {selectedJob.url && (
                          <a href={selectedJob.url} target="_blank" rel="noopener noreferrer" style={{ color: '#45a29e', fontSize: '0.85rem', textDecoration: 'underline' }}>
                            Open Posting ↗
                          </a>
                        )}
                      </div>
                      <div style={{ color: '#fff', fontSize: '0.95rem', marginTop: '0.3rem' }}>
                        <strong>{selectedJob.company}</strong> • <span style={{ color: '#c5c6c7' }}>{selectedJob.location}</span> • <span style={{ color: '#66fcf1' }}>{selectedJob.portal}</span>
                      </div>
                    </div>

                    {/* Quick AI Prep Action */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 'bold' }}>Job Description</span>
                      <button
                        onClick={() => handleGeneratePrep(selectedJob)}
                        disabled={prepLoading === selectedJob.id}
                        style={{
                          background: 'linear-gradient(135deg, #66fcf1, #45a29e)',
                          color: '#0b0c10',
                          border: 'none',
                          padding: '6px 14px',
                          borderRadius: '4px',
                          fontWeight: 'bold',
                          fontSize: '0.8rem',
                          cursor: 'pointer'
                        }}
                      >
                        {prepLoading === selectedJob.id ? '⚡ Generating Prep...' : '⚡ Generate 1-Page Prep'}
                      </button>
                    </div>

                    <div style={{ background: '#0b0c10', padding: '1rem', borderRadius: '6px', fontSize: '0.85rem', color: '#c5c6c7', maxHeight: '180px', overflowY: 'auto', whiteSpace: 'pre-line', lineHeight: 1.5 }}>
                      {selectedJob.description || 'No detailed description stored.'}
                    </div>

                    {prepData[selectedJob.id] && (
                      <div style={{ background: '#0b0c10', padding: '1.25rem', borderRadius: '6px', border: '1px solid #50c878' }}>
                        <h3 style={{ margin: '0 0 0.75rem 0', color: '#50c878', fontSize: '1rem' }}>🤖 Interview Prep Cheat Sheet</h3>
                        <div className="markdown-body" style={{ color: '#c5c6c7', fontSize: '0.85rem' }}>
                          <ReactMarkdown>{prepData[selectedJob.id]}</ReactMarkdown>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div style={{ textAlign: 'center', color: '#888', marginTop: '3rem' }}>Select a job card on the left to inspect details.</div>
                )}
              </div>
            </div>

            {/* MANUAL JOB ADD MODAL */}
            {showAddJobModal && (
              <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
                <form onSubmit={handleSaveManualJob} style={{ background: '#1f2833', border: '1px solid #66fcf1', borderRadius: '8px', padding: '1.5rem', width: '520px', maxHeight: '90vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem', boxShadow: '0 0 20px rgba(102, 252, 241, 0.2)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 style={{ margin: 0, color: '#66fcf1' }}>🔗 Add Manual Job Application</h3>
                    <button type="button" onClick={() => setShowAddJobModal(false)} style={{ background: 'transparent', border: 'none', color: '#c5c6c7', fontSize: '1.2rem', cursor: 'pointer' }}>✕</button>
                  </div>

                  {/* URL Input + Auto Fetch Button */}
                  <div style={{ background: '#0b0c10', padding: '0.75rem', borderRadius: '6px', border: '1px solid #45a29e' }}>
                    <label style={{ display: 'block', color: '#66fcf1', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '4px' }}>
                      Paste Job Posting Link (Naukri, Indeed, Internshala, etc.):
                    </label>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <input
                        type="url"
                        placeholder="https://www.naukri.com/job-listings-..."
                        value={manualUrl}
                        onChange={(e) => setManualUrl(e.target.value)}
                        style={{ flex: 1, padding: '8px', background: '#1f2833', border: '1px solid #45a29e', color: '#fff', borderRadius: '4px', fontSize: '0.85rem' }}
                      />
                      <button
                        type="button"
                        onClick={handleFetchJobFromUrl}
                        disabled={isFetchingUrl || !manualUrl.trim()}
                        style={{ background: '#66fcf1', color: '#0b0c10', border: 'none', padding: '8px 12px', borderRadius: '4px', fontWeight: 'bold', fontSize: '0.8rem', cursor: 'pointer', whiteSpace: 'nowrap' }}
                      >
                        {isFetchingUrl ? '⚡ Fetching...' : '⚡ Auto-Fetch'}
                      </button>
                    </div>
                    {fetchNotice && <div style={{ color: '#f2a900', fontSize: '0.75rem', marginTop: '6px' }}>{fetchNotice}</div>}
                  </div>

                  {/* Form Fields */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    <div>
                      <label style={{ display: 'block', color: '#c5c6c7', fontSize: '0.8rem', marginBottom: '4px' }}>Company Name *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Uncodemy, Google, TCS"
                        value={manualCompany}
                        onChange={(e) => setManualCompany(e.target.value)}
                        style={{ width: '100%', padding: '8px', background: '#0b0c10', border: '1px solid #45a29e', color: '#fff', borderRadius: '4px' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', color: '#c5c6c7', fontSize: '0.8rem', marginBottom: '4px' }}>Job Title *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Web Developer Intern"
                        value={manualTitle}
                        onChange={(e) => setManualTitle(e.target.value)}
                        style={{ width: '100%', padding: '8px', background: '#0b0c10', border: '1px solid #45a29e', color: '#fff', borderRadius: '4px' }}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    <div>
                      <label style={{ display: 'block', color: '#c5c6c7', fontSize: '0.8rem', marginBottom: '4px' }}>Location</label>
                      <input
                        type="text"
                        placeholder="e.g. Noida / Remote"
                        value={manualLocation}
                        onChange={(e) => setManualLocation(e.target.value)}
                        style={{ width: '100%', padding: '8px', background: '#0b0c10', border: '1px solid #45a29e', color: '#fff', borderRadius: '4px' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', color: '#c5c6c7', fontSize: '0.8rem', marginBottom: '4px' }}>Portal / Source</label>
                      <input
                        type="text"
                        placeholder="e.g. Naukri (Manual), Direct"
                        value={manualPortal}
                        onChange={(e) => setManualPortal(e.target.value)}
                        style={{ width: '100%', padding: '8px', background: '#0b0c10', border: '1px solid #45a29e', color: '#fff', borderRadius: '4px' }}
                      />
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', color: '#c5c6c7', fontSize: '0.8rem', marginBottom: '4px' }}>Job Description (for Interview Bot prep)</label>
                    <textarea
                      rows={4}
                      placeholder="Paste the job requirements, responsibilities, or skills here..."
                      value={manualDesc}
                      onChange={(e) => setManualDesc(e.target.value)}
                      style={{ width: '100%', padding: '8px', background: '#0b0c10', border: '1px solid #45a29e', color: '#fff', borderRadius: '4px', resize: 'vertical' }}
                    />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '0.5rem' }}>
                    <button type="button" onClick={() => setShowAddJobModal(false)} style={{ background: 'transparent', border: '1px solid #888', color: '#fff', padding: '8px 14px', borderRadius: '4px', cursor: 'pointer' }}>Cancel</button>
                    <button type="submit" disabled={isSavingManualJob} style={{ background: 'linear-gradient(135deg, #66fcf1, #45a29e)', color: '#0b0c10', border: 'none', padding: '8px 20px', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer' }}>
                      {isSavingManualJob ? '💾 Saving...' : '💾 Save to Database'}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* 2. 🎯 DEDICATED INTERVIEW PREP & NOTES HUB */}
        {/* ======================================================== */}
        {activeTab === 'interview-prep' && (
          <div className="panel" style={{ height: '720px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid #1f2833', paddingBottom: '0.75rem' }}>
              <div>
                <h2 style={{ margin: 0, color: '#66fcf1', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  🎯 AI Interview Preparation & Notes Hub
                </h2>
                <p style={{ margin: '4px 0 0 0', color: '#c5c6c7', fontSize: '0.85rem' }}>
                  Synchronized cheat sheets, walk-in interview venues, and .ics calendar invites.
                </p>
              </div>
              <button
                onClick={() => setShowAddModal(true)}
                style={{
                  background: 'linear-gradient(135deg, #66fcf1, #45a29e)',
                  color: '#0b0c10',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
              >
                + New Prep Sheet
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '1.5rem', flex: 1, minHeight: 0 }}>
              {/* Left Column: Interview List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', borderRight: '1px solid #1f2833', paddingRight: '1rem', minHeight: 0 }}>
                <input
                  type="text"
                  placeholder="🔍 Search company or skill..."
                  value={interviewSearch}
                  onChange={(e) => setInterviewSearch(e.target.value)}
                  style={{
                    background: '#1f2833',
                    border: '1px solid #45a29e',
                    color: '#fff',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    outline: 'none',
                    fontSize: '0.85rem'
                  }}
                />

                <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                  {filteredInterviews.length === 0 ? (
                    <div style={{ color: '#c5c6c7', textAlign: 'center', padding: '2rem 1rem', fontSize: '0.85rem' }}>
                      No interview sheets found. Click "+ New Prep Sheet" to create one.
                    </div>
                  ) : (
                    filteredInterviews.map((item) => {
                      const isSelected = selectedInterview?.id === item.id;
                      return (
                        <div
                          key={item.id}
                          onClick={() => setSelectedInterview(item)}
                          style={{
                            background: isSelected ? '#1f2833' : '#0b0c10',
                            border: `1px solid ${isSelected ? '#66fcf1' : '#1f2833'}`,
                            borderRadius: '8px',
                            padding: '0.85rem',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            boxShadow: isSelected ? '0 0 10px rgba(102, 252, 241, 0.15)' : 'none'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                            <strong style={{ color: isSelected ? '#66fcf1' : '#fff', fontSize: '0.95rem' }}>{item.company}</strong>
                            {item.has_calendar && <span title="Calendar invite synced" style={{ fontSize: '0.85rem' }}>📅</span>}
                          </div>
                          <div style={{ color: '#c5c6c7', fontSize: '0.8rem', marginBottom: '6px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {item.title}
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem' }}>
                            <span style={{ background: '#50c87822', color: '#50c878', padding: '2px 6px', borderRadius: '4px' }}>
                              {item.portal}
                            </span>
                            <span style={{ color: '#888' }}>
                              {new Date(item.updated_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Right Column: Markdown Cheat Sheet */}
              <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, overflowY: 'auto' }}>
                {selectedInterview ? (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', background: '#1f2833', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
                      <div>
                        <h3 style={{ margin: '0 0 4px 0', color: '#66fcf1', fontSize: '1.25rem' }}>
                          {selectedInterview.company}
                        </h3>
                        <div style={{ color: '#c5c6c7', fontSize: '0.85rem' }}>
                          <strong>Role:</strong> {selectedInterview.title} &nbsp;|&nbsp; <strong>Location:</strong> {selectedInterview.location}
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => handleRegenerateInterview(selectedInterview)}
                          disabled={isRegenerating}
                          style={{
                            background: '#45a29e',
                            color: '#0b0c10',
                            border: 'none',
                            padding: '6px 12px',
                            borderRadius: '4px',
                            fontWeight: 'bold',
                            fontSize: '0.8rem',
                            cursor: 'pointer'
                          }}
                        >
                          {isRegenerating ? '⚡ Regenerating...' : '⚡ Regenerate with AI'}
                        </button>
                      </div>
                    </div>

                    <div
                      className="markdown-body"
                      style={{
                        background: '#0b0c10',
                        border: '1px solid #1f2833',
                        borderRadius: '8px',
                        padding: '1.5rem',
                        color: '#c5c6c7',
                        lineHeight: 1.6,
                        fontSize: '0.9rem'
                      }}
                    >
                      <ReactMarkdown>{selectedInterview.content}</ReactMarkdown>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#c5c6c7' }}>
                    Select an interview from the left panel to inspect its preparation notes.
                  </div>
                )}
              </div>
            </div>

            {/* Add Modal */}
            {showAddModal && (
              <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
                <form onSubmit={handleCreateNewPrep} style={{ background: '#1f2833', border: '1px solid #66fcf1', borderRadius: '8px', padding: '1.5rem', width: '450px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <h3 style={{ margin: 0, color: '#66fcf1' }}>Create New Interview Prep Sheet</h3>
                  <div>
                    <label style={{ display: 'block', color: '#c5c6c7', fontSize: '0.8rem', marginBottom: '4px' }}>Company Name *</label>
                    <input
                      type="text"
                      required
                      value={newCompany}
                      onChange={(e) => setNewCompany(e.target.value)}
                      placeholder="e.g. Google, Microsoft, Uncodemy"
                      style={{ width: '100%', padding: '8px', background: '#0b0c10', border: '1px solid #45a29e', color: '#fff', borderRadius: '4px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', color: '#c5c6c7', fontSize: '0.8rem', marginBottom: '4px' }}>Role / Job Title</label>
                    <input
                      type="text"
                      value={newRole}
                      onChange={(e) => setNewRole(e.target.value)}
                      placeholder="e.g. Python Developer, Full Stack Intern"
                      style={{ width: '100%', padding: '8px', background: '#0b0c10', border: '1px solid #45a29e', color: '#fff', borderRadius: '4px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', color: '#c5c6c7', fontSize: '0.8rem', marginBottom: '4px' }}>Job Description / Key Topics</label>
                    <textarea
                      rows={4}
                      value={newDesc}
                      onChange={(e) => setNewDesc(e.target.value)}
                      placeholder="Paste JD or key skills to focus on..."
                      style={{ width: '100%', padding: '8px', background: '#0b0c10', border: '1px solid #45a29e', color: '#fff', borderRadius: '4px', resize: 'vertical' }}
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '0.5rem' }}>
                    <button type="button" onClick={() => setShowAddModal(false)} style={{ background: 'transparent', border: '1px solid #888', color: '#fff', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer' }}>Cancel</button>
                    <button type="submit" disabled={isCreatingPrep} style={{ background: '#66fcf1', color: '#0b0c10', border: 'none', padding: '6px 16px', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer' }}>
                      {isCreatingPrep ? 'Generating...' : 'Generate Sheet'}
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* 3. 📬 OUTREACH HUB */}
        {/* ======================================================== */}
        {activeTab === 'outreach' && (
          <div className="panel analytics-panel" style={{ minHeight: '600px' }}>
            <h2>📬 LinkedIn & Recruiter Outreach Engine</h2>
            <div className="analytics-summary" style={{ marginBottom: '1.5rem' }}>
              <div className="analytics-card" style={{ borderColor: '#45a29e' }}>
                <div className="analytics-label">Total Sent</div>
                <div className="analytics-val">{outreachData?.stats?.totalSent ?? '40'}</div>
              </div>
              <div className="analytics-card" style={{ borderColor: '#50c878' }}>
                <div className="analytics-label">Replies Received</div>
                <div className="analytics-val" style={{ color: '#50c878' }}>{outreachData?.stats?.totalReplies ?? '0'}</div>
              </div>
              <div className="analytics-card" style={{ borderColor: '#f2a900' }}>
                <div className="analytics-label">Pending Followups</div>
                <div className="analytics-val" style={{ color: '#f2a900' }}>{outreachData?.stats?.pendingFollowups ?? '0'}</div>
              </div>
            </div>

            {outreachData?.recentReplies?.length > 0 && (
              <div style={{ marginBottom: '1.5rem' }}>
                <h3 style={{ color: '#50c878', marginBottom: '0.75rem' }}>📥 Recent Direct Messages & Replies</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {outreachData.recentReplies.map((r: any, i: number) => (
                    <div key={i} style={{ background: '#1f2833', border: '1px solid #45a29e', borderRadius: '6px', padding: '0.75rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                        <strong style={{ color: '#66fcf1' }}>{r.recipient}</strong>
                        <span style={{ fontSize: '0.75rem', color: '#c5c6c7' }}>{new Date(r.received_at).toLocaleDateString()}</span>
                      </div>
                      <div style={{ color: '#fff', fontWeight: 'bold', fontSize: '0.9rem' }}>{r.subject}</div>
                      <div style={{ color: '#c5c6c7', fontSize: '0.85rem' }}>{r.snippet}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* 4. 🧠 DAILY UPSKILL */}
        {/* ======================================================== */}
        {activeTab === 'upskill' && (
          <div className="panel upskill-panel markdown-body" style={{ minHeight: '600px', padding: '2rem' }}>
            <ReactMarkdown>{lesson || "No lesson generated today. Check back tomorrow!"}</ReactMarkdown>
          </div>
        )}

        {/* ======================================================== */}
        {/* 5. 💬 JARVIS AI CHAT */}
        {/* ======================================================== */}
        {activeTab === 'chat' && (
          <div className="panel chat-panel" style={{ height: '700px', display: 'flex', flexDirection: 'column' }}>
            <div className="chat-history" style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {messages.map((m, i) => (
                <div key={i} className={`chat-message ${m.role}`} style={{ display: 'flex', gap: '10px' }}>
                  <div className="avatar" style={{ fontSize: '1.5rem' }}>{m.role === 'assistant' ? '🤖' : '👤'}</div>
                  <div className="message-bubble" style={{ background: m.role === 'assistant' ? '#1f2833' : '#45a29e22', border: `1px solid ${m.role === 'assistant' ? '#45a29e' : '#66fcf1'}`, borderRadius: '8px', padding: '0.75rem 1rem', color: '#fff', maxWidth: '80%' }}>
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="chat-message assistant" style={{ display: 'flex', gap: '10px' }}>
                  <div className="avatar">🤖</div>
                  <div className="message-bubble" style={{ background: '#1f2833', padding: '0.75rem 1rem', borderRadius: '8px', color: '#66fcf1' }}>
                    Jarvis is thinking...
                  </div>
                </div>
              )}
            </div>
            <form className="chat-input-bar" onSubmit={handleSendMessage} style={{ display: 'flex', gap: '8px', padding: '0.75rem', borderTop: '1px solid #1f2833' }}>
              <input
                type="text"
                placeholder="Ask Jarvis anything about your applications, interviews, or system status..."
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                style={{ flex: 1, padding: '10px', background: '#0b0c10', border: '1px solid #45a29e', color: '#fff', borderRadius: '6px' }}
              />
              <button type="submit" disabled={isLoading} style={{ background: '#66fcf1', color: '#0b0c10', border: 'none', padding: '10px 20px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>
                SEND
              </button>
            </form>
          </div>
        )}

      </div>
    </main>
  );
}
