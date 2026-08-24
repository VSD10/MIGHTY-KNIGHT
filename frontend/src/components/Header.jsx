import React, { useState, useEffect } from 'react';
import { ShieldAlert, Calendar, FileSpreadsheet, Play, CheckCircle, Clock, Download, HardDrive, Sparkles, Layers, Users, BarChart3, MessageSquare } from 'lucide-react';
import { getDownloadTemplateUrl, getDataSummary } from '../services/api';

export default function Header({ scheduleStatus, onStatusToggle, activeTab, setActiveTab, onUploadClick, onScheduleClick, loading }) {
  const [activeFileInfo, setActiveFileInfo] = useState(null);

  useEffect(() => {
    fetchActiveFileInfo();
  }, []);

  const fetchActiveFileInfo = async () => {
    try {
      const summary = await getDataSummary();
      if (summary) {
        setActiveFileInfo(summary);
      }
    } catch (err) {
      console.error("Failed to fetch active file summary:", err);
    }
  };

  return (
    <header className="glass-panel" style={{ padding: '20px 32px', marginBottom: '28px', border: '1px solid var(--border-gold)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '20px' }}>
        {/* Brand Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            className="knight-logo"
            style={{
              width: '52px',
              height: '52px',
              borderRadius: '16px',
              background: 'linear-gradient(135deg, #fbbf24 0%, #d97706 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 'var(--shadow-gold)',
              border: '1px solid rgba(255,255,255,0.2)'
            }}
          >
            <span style={{ fontSize: '30px', filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.5))' }}>♞</span>
          </div>

          <div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 900, color: '#fff', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '12px' }}>
              MIGHTY KNIGHT
              <span className="badge badge-gold" style={{ fontSize: '0.7rem', padding: '3px 10px' }}>
                <Sparkles size={12} style={{ marginRight: '4px' }} /> Rules Engine v1.0
              </span>
            </h1>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Intelligent Chess Academy Scheduling, Capacity Optimization & Multi-Channel Dispatch
            </p>
          </div>
        </div>

        {/* Schedule Controls & Active Dataset Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {activeFileInfo && (
            <div style={{
              background: 'rgba(251, 191, 36, 0.12)',
              border: '1px solid rgba(251, 191, 36, 0.35)',
              borderRadius: 'var(--radius-md)',
              padding: '8px 14px',
              fontSize: '0.8rem',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
            }}>
              <HardDrive size={16} style={{ color: 'var(--accent-gold)' }} />
              <span>Active Dataset: <strong>{activeFileInfo.filename}</strong> ({activeFileInfo.students_count} Students · {activeFileInfo.coaches_count} Coaches)</span>
            </div>
          )}

          {scheduleStatus && (
            <button
              onClick={onStatusToggle}
              className={`badge ${scheduleStatus === 'Finalized' ? 'badge-success' : 'badge-gold'}`}
              style={{ padding: '9px 16px', cursor: 'pointer', border: 'none', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem' }}
            >
              {scheduleStatus === 'Finalized' ? <CheckCircle size={16} /> : <Clock size={16} />}
              Status: {scheduleStatus}
            </button>
          )}

          <a
            href={getDownloadTemplateUrl()}
            download="mighty_knight_template.xlsx"
            className="btn btn-secondary"
            style={{ textDecoration: 'none', color: '#fff', padding: '10px 16px' }}
          >
            <Download size={16} /> Template
          </a>

          <button onClick={onUploadClick} className="btn btn-secondary" style={{ padding: '10px 16px' }}>
            <FileSpreadsheet size={16} /> Upload Excel
          </button>

          <button onClick={onScheduleClick} disabled={loading} className="btn btn-primary" style={{ padding: '10px 20px' }}>
            <Play size={16} /> {loading ? 'Scheduling...' : 'Run Engine'}
          </button>
        </div>
      </div>

      {/* Futuristic Navigation Tabs Bar */}
      <div style={{ display: 'flex', gap: '10px', marginTop: '24px', borderTop: '1px solid var(--border-color)', paddingTop: '18px', overflowX: 'auto' }}>
        <button
          onClick={() => setActiveTab('output1')}
          className={`btn ${activeTab === 'output1' ? 'btn-primary' : 'btn-secondary'}`}
          style={activeTab === 'output1' ? { background: 'linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)', color: '#fff', border: 'none' } : {}}
        >
          <MessageSquare size={16} /> Output 1 — Coach Schedule (WhatsApp)
        </button>

        <button
          onClick={() => setActiveTab('output2')}
          className={`btn ${activeTab === 'output2' ? 'btn-primary' : 'btn-secondary'}`}
          style={activeTab === 'output2' ? { background: 'linear-gradient(135deg, #fbbf24 0%, #d97706 100%)', color: '#000', border: 'none' } : {}}
        >
          <Layers size={16} /> Output 2 — Detailed Admin Schedule
        </button>

        <button
          onClick={() => setActiveTab('output3')}
          className={`btn ${activeTab === 'output3' ? 'btn-danger' : 'btn-secondary'}`}
          style={activeTab === 'output3' ? { background: 'linear-gradient(135deg, #f43f5e 0%, #be123c 100%)', color: '#fff', border: 'none', boxShadow: '0 4px 18px rgba(244,63,94,0.4)' } : {}}
        >
          <ShieldAlert size={16} className="pulse-icon" /> Output 3 — Unscheduled Attention
        </button>

        <button
          onClick={() => setActiveTab('coachWorkload')}
          className={`btn ${activeTab === 'coachWorkload' ? 'btn-primary' : 'btn-secondary'}`}
          style={activeTab === 'coachWorkload' ? { background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)', color: '#fff', border: 'none' } : {}}
        >
          <BarChart3 size={16} /> Output 4 — Coach Workload & Hours
        </button>

        <button
          onClick={() => setActiveTab('masterData')}
          className={`btn ${activeTab === 'masterData' ? 'btn-primary' : 'btn-secondary'}`}
          style={activeTab === 'masterData' ? { background: 'linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)', color: '#fff', border: 'none' } : {}}
        >
          <Users size={16} /> Master Data (Students & Coaches)
        </button>
      </div>
    </header>
  );
}
