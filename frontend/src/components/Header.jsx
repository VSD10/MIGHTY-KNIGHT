import React, { useState, useEffect } from 'react';
import { ShieldAlert, Calendar, FileSpreadsheet, Play, CheckCircle, Clock, Download, HardDrive } from 'lucide-react';
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
    <header className="glass-panel" style={{ padding: '16px 28px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(245, 158, 11, 0.4)'
          }}>
            <span style={{ fontSize: '24px' }}>♞</span>
          </div>
          <div>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '10px' }}>
              MIGHTY KNIGHT
              <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(255, 255, 255, 0.1)', color: '#9ca3af', fontWeight: 600 }}>
                v1.0 Rules Engine
              </span>
            </h1>
            <p style={{ fontSize: '0.825rem', color: '#9ca3af' }}>
              Dynamic Academy Scheduling Engine for Chess Academies
            </p>
          </div>
        </div>

        {/* Schedule Controls & Active Dataset Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {activeFileInfo && (
            <div style={{
              background: 'rgba(245, 158, 11, 0.15)',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              borderRadius: 'var(--radius-md)',
              padding: '6px 12px',
              fontSize: '0.775rem',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              <HardDrive size={14} style={{ color: 'var(--accent-gold)' }} />
              <span>Active File: <strong>{activeFileInfo.filename}</strong> ({activeFileInfo.students_count} students, {activeFileInfo.coaches_count} coaches)</span>
            </div>
          )}

          {scheduleStatus && (
            <button
              onClick={onStatusToggle}
              className={`badge ${scheduleStatus === 'Finalized' ? 'badge-success' : 'badge-gold'}`}
              style={{ padding: '8px 14px', cursor: 'pointer', border: 'none', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {scheduleStatus === 'Finalized' ? <CheckCircle size={14} /> : <Clock size={14} />}
              Status: {scheduleStatus} (Click to toggle)
            </button>
          )}

          <a
            href={getDownloadTemplateUrl()}
            download="mighty_knight_template.xlsx"
            className="btn btn-secondary"
            style={{ textDecoration: 'none', color: '#fff' }}
          >
            <Download size={16} /> Excel Format
          </a>

          <button onClick={onUploadClick} className="btn btn-secondary">
            <FileSpreadsheet size={16} /> Upload Excel Data
          </button>

          <button onClick={onScheduleClick} disabled={loading} className="btn btn-primary">
            <Play size={16} /> {loading ? 'Scheduling...' : 'Run Engine'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
        <button
          onClick={() => setActiveTab('output1')}
          className={`btn ${activeTab === 'output1' ? 'btn-primary' : 'btn-secondary'}`}
        >
          📱 Output 1 — Coach Schedule (WhatsApp)
        </button>

        <button
          onClick={() => setActiveTab('output2')}
          className={`btn ${activeTab === 'output2' ? 'btn-primary' : 'btn-secondary'}`}
        >
          📋 Output 2 — Detailed Admin Schedule
        </button>

        <button
          onClick={() => setActiveTab('output3')}
          className={`btn ${activeTab === 'output3' ? 'btn-danger' : 'btn-secondary'}`}
          style={activeTab === 'output3' ? { background: '#ef4444', color: '#fff' } : {}}
        >
          <ShieldAlert size={16} className="pulse-icon" /> Output 3 — Unscheduled Attention
        </button>
      </div>
    </header>
  );
}
