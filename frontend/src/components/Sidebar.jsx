import React from 'react';
import { MessageSquare, Layers, ShieldAlert, BarChart3, Users, Play, FileSpreadsheet, Download, CheckCircle, Clock, Sparkles, HardDrive, Settings } from 'lucide-react';
import { getDownloadTemplateUrl } from '../services/api';

export default function Sidebar({
  activeTab,
  setActiveTab,
  activeFileInfo,
  scheduleStatus,
  onStatusToggle,
  onUploadClick,
  onScheduleClick,
  loading,
  attentionCount
}) {
  return (
    <aside
      className="glass-panel"
      style={{
        width: '280px',
        minWidth: '280px',
        height: 'calc(100vh - 48px)',
        position: 'sticky',
        top: '24px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '24px 18px',
        border: '1px solid var(--border-gold)',
        zIndex: 100
      }}
    >
      {/* Top Section: Brand & Active File Pill */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid var(--border-color)' }}>
          <div
            className="knight-logo"
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '14px',
              background: 'linear-gradient(135deg, #fbbf24 0%, #d97706 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 'var(--shadow-gold)',
              border: '1px solid rgba(255,255,255,0.2)'
            }}
          >
            <span style={{ fontSize: '26px', filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.5))' }}>♞</span>
          </div>

          <div>
            <h1 style={{ fontSize: '1.35rem', fontWeight: 900, color: '#fff', letterSpacing: '-0.02em' }}>
              MIGHTY KNIGHT
            </h1>
            <span className="badge badge-gold" style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
              <Sparkles size={10} style={{ marginRight: '4px' }} /> Rules Engine v1.0
            </span>
          </div>
        </div>

        {/* Active Dataset Pill */}
        {activeFileInfo && (
          <div
            style={{
              background: 'rgba(251, 191, 36, 0.1)',
              border: '1px solid rgba(251, 191, 36, 0.3)',
              borderRadius: 'var(--radius-md)',
              padding: '10px 12px',
              marginBottom: '20px',
              fontSize: '0.775rem',
              color: '#fff'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-gold)', fontWeight: 800, marginBottom: '4px' }}>
              <HardDrive size={14} /> ACTIVE STORE
            </div>
            <div style={{ fontWeight: 700, truncate: 'true', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {activeFileInfo.filename}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {activeFileInfo.students_count} Students · {activeFileInfo.coaches_count} Coaches
            </div>
          </div>
        )}

        {/* Primary Action Button: Run Engine */}
        <button
          onClick={onScheduleClick}
          disabled={loading}
          className="btn btn-primary"
          style={{ width: '100%', padding: '12px', marginBottom: '20px', fontSize: '0.9rem', fontWeight: 800, display: 'flex', justifyContent: 'center' }}
        >
          <Play size={18} /> {loading ? 'Scheduling Engine...' : 'Run Scheduling Engine'}
        </button>

        {/* Navigation Items */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <span style={{ fontSize: '0.675rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px', paddingLeft: '8px' }}>
            OPERATIONS NAVIGATION
          </span>

          <button
            onClick={() => setActiveTab('output1')}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              border: activeTab === 'output1' ? '1px solid var(--accent-blue)' : '1px solid transparent',
              background: activeTab === 'output1' ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.2) 0%, rgba(2, 132, 199, 0.2) 100%)' : 'transparent',
              color: activeTab === 'output1' ? '#fff' : 'var(--text-secondary)',
              fontWeight: activeTab === 'output1' ? 800 : 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              textAlign: 'left',
              transition: 'all 0.2s ease'
            }}
          >
            <MessageSquare size={16} style={{ color: activeTab === 'output1' ? 'var(--accent-blue)' : 'inherit' }} />
            Output 1 — WhatsApp Schedule
          </button>

          <button
            onClick={() => setActiveTab('output2')}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              border: activeTab === 'output2' ? '1px solid var(--accent-gold)' : '1px solid transparent',
              background: activeTab === 'output2' ? 'linear-gradient(135deg, rgba(251, 191, 36, 0.2) 0%, rgba(217, 119, 6, 0.2) 100%)' : 'transparent',
              color: activeTab === 'output2' ? '#fff' : 'var(--text-secondary)',
              fontWeight: activeTab === 'output2' ? 800 : 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              textAlign: 'left',
              transition: 'all 0.2s ease'
            }}
          >
            <Layers size={16} style={{ color: activeTab === 'output2' ? 'var(--accent-gold)' : 'inherit' }} />
            Output 2 — Admin Matrix
          </button>

          <button
            onClick={() => setActiveTab('output3')}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              border: activeTab === 'output3' ? '1px solid var(--status-danger)' : '1px solid transparent',
              background: activeTab === 'output3' ? 'linear-gradient(135deg, rgba(244, 63, 94, 0.2) 0%, rgba(190, 18, 60, 0.2) 100%)' : 'transparent',
              color: activeTab === 'output3' ? '#fff' : 'var(--text-secondary)',
              fontWeight: activeTab === 'output3' ? 800 : 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              textAlign: 'left',
              transition: 'all 0.2s ease'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <ShieldAlert size={16} className={attentionCount > 0 ? "pulse-icon" : ""} style={{ color: 'var(--status-danger)' }} />
              Output 3 — Attention
            </div>
            {attentionCount > 0 && (
              <span className="badge badge-danger" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                {attentionCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('coachWorkload')}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              border: activeTab === 'coachWorkload' ? '1px solid var(--status-success)' : '1px solid transparent',
              background: activeTab === 'coachWorkload' ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(4, 120, 87, 0.2) 100%)' : 'transparent',
              color: activeTab === 'coachWorkload' ? '#fff' : 'var(--text-secondary)',
              fontWeight: activeTab === 'coachWorkload' ? 800 : 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              textAlign: 'left',
              transition: 'all 0.2s ease'
            }}
          >
            <BarChart3 size={16} style={{ color: activeTab === 'coachWorkload' ? 'var(--status-success)' : 'inherit' }} />
            Output 4 — Coach Workload
          </button>

          <button
            onClick={() => setActiveTab('masterData')}
            style={{
              width: '100%',
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              border: activeTab === 'masterData' ? '1px solid #a855f7' : '1px solid transparent',
              background: activeTab === 'masterData' ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(126, 34, 206, 0.2) 100%)' : 'transparent',
              color: activeTab === 'masterData' ? '#fff' : 'var(--text-secondary)',
              fontWeight: activeTab === 'masterData' ? 800 : 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              textAlign: 'left',
              transition: 'all 0.2s ease'
            }}
          >
            <Users size={16} style={{ color: activeTab === 'masterData' ? '#a855f7' : 'inherit' }} />
            Master Data Hub
          </button>
        </div>
      </div>

      {/* Bottom Section: Ingestion & System Controls */}
      <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <button
          onClick={onStatusToggle}
          className={`badge ${scheduleStatus === 'Finalized' ? 'badge-success' : 'badge-gold'}`}
          style={{ width: '100%', padding: '10px', cursor: 'pointer', border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', fontSize: '0.775rem' }}
        >
          {scheduleStatus === 'Finalized' ? <CheckCircle size={14} /> : <Clock size={14} />}
          Status: {scheduleStatus}
        </button>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          <button onClick={onUploadClick} className="btn btn-secondary" style={{ padding: '8px', fontSize: '0.75rem', justifyContent: 'center' }}>
            <FileSpreadsheet size={14} /> Upload
          </button>

          <a
            href={getDownloadTemplateUrl()}
            download="mighty_knight_template.xlsx"
            className="btn btn-secondary"
            style={{ padding: '8px', fontSize: '0.75rem', justifyContent: 'center', textDecoration: 'none', color: '#fff' }}
          >
            <Download size={14} /> Template
          </a>
        </div>
      </div>
    </aside>
  );
}
