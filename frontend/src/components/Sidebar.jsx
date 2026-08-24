import React from 'react';
import { MessageSquare, Layers, ShieldAlert, BarChart3, Users, Play, FileSpreadsheet, CheckCircle, Clock, Sparkles, HardDrive, ChevronLeft, ChevronRight } from 'lucide-react';

export default function Sidebar({
  activeTab,
  setActiveTab,
  activeFileInfo,
  scheduleStatus,
  onStatusToggle,
  onUploadClick,
  onScheduleClick,
  loading,
  attentionCount,
  isCollapsed,
  onToggleCollapse
}) {
  const sidebarWidth = isCollapsed ? '80px' : '280px';

  return (
    <aside
      className="glass-panel"
      style={{
        width: sidebarWidth,
        minWidth: sidebarWidth,
        height: 'calc(100vh - 48px)',
        position: 'sticky',
        top: '24px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: isCollapsed ? '16px 10px' : '20px 16px',
        border: '1px solid var(--border-gold)',
        zIndex: 100,
        transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1), padding 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        overflowY: 'auto',
        overflowX: 'hidden'
      }}
    >
      {/* Top Section: Official Brand Logo & Retract Button */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: isCollapsed ? 'center' : 'space-between', marginBottom: '16px', paddingBottom: '14px', borderBottom: '1px solid var(--border-color)' }}>
          {!isCollapsed && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <img
                src="/CHESS.png"
                alt="Mighty Knight Official Logo"
                className="knight-logo"
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  border: '1px solid var(--accent-gold)',
                  boxShadow: 'var(--shadow-gold)',
                  objectFit: 'cover'
                }}
              />

              <div>
                <h1 style={{ fontSize: '1.2rem', fontWeight: 900, color: '#fff', letterSpacing: '-0.02em', lineHeight: '1.1' }}>
                  MIGHTY KNIGHT
                </h1>
                <span className="badge badge-gold" style={{ fontSize: '0.6rem', padding: '1px 6px', marginTop: '2px' }}>
                  <Sparkles size={8} style={{ marginRight: '3px' }} /> v1.0 Engine
                </span>
              </div>
            </div>
          )}

          {isCollapsed && (
            <img
              src="/CHESS.png"
              alt="Mighty Knight Logo"
              className="knight-logo"
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '10px',
                border: '1px solid var(--accent-gold)',
                boxShadow: 'var(--shadow-gold)',
                cursor: 'pointer',
                objectFit: 'cover'
              }}
              onClick={onToggleCollapse}
              title="Expand Sidebar"
            />
          )}

          {/* Toggle Retract Button */}
          {!isCollapsed && (
            <button
              onClick={onToggleCollapse}
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--accent-gold)',
                padding: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title="Collapse Sidebar"
            >
              <ChevronLeft size={18} />
            </button>
          )}
        </div>

        {/* Active Dataset Pill (Expanded Mode) */}
        {!isCollapsed && activeFileInfo && (
          <div
            style={{
              background: 'rgba(250, 204, 21, 0.08)',
              border: '1px solid rgba(250, 204, 21, 0.25)',
              borderRadius: 'var(--radius-md)',
              padding: '8px 12px',
              marginBottom: '16px',
              fontSize: '0.75rem',
              color: '#fff'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-gold)', fontWeight: 800, marginBottom: '2px' }}>
              <HardDrive size={13} /> ACTIVE STORE
            </div>
            <div style={{ fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {activeFileInfo.filename}
            </div>
            <div style={{ fontSize: '0.675rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {activeFileInfo.students_count} Students · {activeFileInfo.coaches_count} Coaches
            </div>
          </div>
        )}

        {/* Primary Action Button: Run Engine */}
        <button
          onClick={onScheduleClick}
          disabled={loading}
          className="btn btn-primary"
          style={{
            width: '100%',
            padding: isCollapsed ? '10px 0' : '10px 14px',
            marginBottom: '16px',
            fontSize: isCollapsed ? '0.8rem' : '0.85rem',
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px'
          }}
          title={isCollapsed ? "Run Scheduling Engine" : ""}
        >
          <Play size={16} /> {!isCollapsed && (loading ? 'Scheduling Engine...' : 'Run Engine')}
        </button>

        {/* Navigation Items */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {!isCollapsed && (
            <span style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '2px', paddingLeft: '4px' }}>
              OPERATIONS NAVIGATION
            </span>
          )}

          {/* Output 1 Tab */}
          <button
            onClick={() => setActiveTab('output1')}
            title={isCollapsed ? "Output 1 — WhatsApp Schedule" : ""}
            style={{
              width: '100%',
              padding: isCollapsed ? '10px 0' : '9px 12px',
              borderRadius: 'var(--radius-md)',
              border: activeTab === 'output1' ? '1px solid var(--accent-blue)' : '1px solid transparent',
              background: activeTab === 'output1' ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.2) 0%, rgba(2, 132, 199, 0.2) 100%)' : 'transparent',
              color: activeTab === 'output1' ? '#fff' : 'var(--text-secondary)',
              fontWeight: activeTab === 'output1' ? 800 : 600,
              fontSize: '0.825rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: isCollapsed ? 'center' : 'flex-start',
              gap: '10px',
              transition: 'all 0.2s ease'
            }}
          >
            <MessageSquare size={16} style={{ color: activeTab === 'output1' ? 'var(--accent-blue)' : 'inherit' }} />
            {!isCollapsed && <span>Output 1 — WhatsApp</span>}
          </button>

          {/* Output 2 Tab */}
          <button
            onClick={() => setActiveTab('output2')}
            title={isCollapsed ? "Output 2 — Admin Matrix" : ""}
            style={{
              width: '100%',
              padding: isCollapsed ? '10px 0' : '9px 12px',
              borderRadius: 'var(--radius-md)',
              border: activeTab === 'output2' ? '1px solid var(--accent-gold)' : '1px solid transparent',
              background: activeTab === 'output2' ? 'linear-gradient(135deg, rgba(250, 204, 21, 0.2) 0%, rgba(217, 119, 6, 0.2) 100%)' : 'transparent',
              color: activeTab === 'output2' ? '#fff' : 'var(--text-secondary)',
              fontWeight: activeTab === 'output2' ? 800 : 600,
              fontSize: '0.825rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: isCollapsed ? 'center' : 'flex-start',
              gap: '10px',
              transition: 'all 0.2s ease'
            }}
          >
            <Layers size={16} style={{ color: activeTab === 'output2' ? 'var(--accent-gold)' : 'inherit' }} />
            {!isCollapsed && <span>Output 2 — Admin Matrix</span>}
          </button>

          {/* Output 3 Tab */}
          <button
            onClick={() => setActiveTab('output3')}
            title={isCollapsed ? "Output 3 — Attention" : ""}
            style={{
              width: '100%',
              padding: isCollapsed ? '10px 0' : '9px 12px',
              borderRadius: 'var(--radius-md)',
              border: activeTab === 'output3' ? '1px solid var(--status-danger)' : '1px solid transparent',
              background: activeTab === 'output3' ? 'linear-gradient(135deg, rgba(244, 63, 94, 0.2) 0%, rgba(190, 18, 60, 0.2) 100%)' : 'transparent',
              color: activeTab === 'output3' ? '#fff' : 'var(--text-secondary)',
              fontWeight: activeTab === 'output3' ? 800 : 600,
              fontSize: '0.825rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: isCollapsed ? 'center' : 'space-between',
              gap: '10px',
              transition: 'all 0.2s ease'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', justifyContent: isCollapsed ? 'center' : 'flex-start', width: isCollapsed ? '100%' : 'auto' }}>
              <ShieldAlert size={16} className={attentionCount > 0 ? "pulse-icon" : ""} style={{ color: 'var(--status-danger)' }} />
              {!isCollapsed && <span>Output 3 — Attention</span>}
            </div>
            {!isCollapsed && attentionCount > 0 && (
              <span className="badge badge-danger" style={{ fontSize: '0.625rem', padding: '2px 6px' }}>
                {attentionCount}
              </span>
            )}
          </button>

          {/* Output 4 Tab */}
          <button
            onClick={() => setActiveTab('coachWorkload')}
            title={isCollapsed ? "Output 4 — Coach Workload" : ""}
            style={{
              width: '100%',
              padding: isCollapsed ? '10px 0' : '9px 12px',
              borderRadius: 'var(--radius-md)',
              border: activeTab === 'coachWorkload' ? '1px solid var(--status-success)' : '1px solid transparent',
              background: activeTab === 'coachWorkload' ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(4, 120, 87, 0.2) 100%)' : 'transparent',
              color: activeTab === 'coachWorkload' ? '#fff' : 'var(--text-secondary)',
              fontWeight: activeTab === 'coachWorkload' ? 800 : 600,
              fontSize: '0.825rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: isCollapsed ? 'center' : 'flex-start',
              gap: '10px',
              transition: 'all 0.2s ease'
            }}
          >
            <BarChart3 size={16} style={{ color: activeTab === 'coachWorkload' ? 'var(--status-success)' : 'inherit' }} />
            {!isCollapsed && <span>Output 4 — Coach Workload</span>}
          </button>

          {/* Master Data Tab */}
          <button
            onClick={() => setActiveTab('masterData')}
            title={isCollapsed ? "Master Data Hub" : ""}
            style={{
              width: '100%',
              padding: isCollapsed ? '10px 0' : '9px 12px',
              borderRadius: 'var(--radius-md)',
              border: activeTab === 'masterData' ? '1px solid #a855f7' : '1px solid transparent',
              background: activeTab === 'masterData' ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(126, 34, 206, 0.2) 100%)' : 'transparent',
              color: activeTab === 'masterData' ? '#fff' : 'var(--text-secondary)',
              fontWeight: activeTab === 'masterData' ? 800 : 600,
              fontSize: '0.825rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: isCollapsed ? 'center' : 'flex-start',
              gap: '10px',
              transition: 'all 0.2s ease'
            }}
          >
            <Users size={16} style={{ color: activeTab === 'masterData' ? '#a855f7' : 'inherit' }} />
            {!isCollapsed && <span>Master Data Hub</span>}
          </button>
        </div>
      </div>

      {/* Bottom Section: Ingestion & System Controls */}
      <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '14px', marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {isCollapsed ? (
          <button
            onClick={onToggleCollapse}
            className="btn btn-secondary"
            style={{ width: '100%', padding: '8px 0', justifyContent: 'center' }}
            title="Expand Sidebar"
          >
            <ChevronRight size={16} />
          </button>
        ) : (
          <>
            <button
              onClick={onStatusToggle}
              className={`badge ${scheduleStatus === 'Finalized' ? 'badge-success' : 'badge-gold'}`}
              style={{ width: '100%', padding: '8px', cursor: 'pointer', border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', fontSize: '0.75rem' }}
            >
              {scheduleStatus === 'Finalized' ? <CheckCircle size={14} /> : <Clock size={14} />}
              Status: {scheduleStatus}
            </button>

            {/* FULLY VISIBLE SLEEK UPLOAD BUTTON */}
            <button
              onClick={onUploadClick}
              className="btn btn-secondary"
              style={{ width: '100%', padding: '9px', fontSize: '0.8rem', justifyContent: 'center', borderColor: 'var(--accent-gold)', color: 'var(--accent-gold)', fontWeight: 800 }}
            >
              <FileSpreadsheet size={16} /> Upload Excel Data
            </button>
          </>
        )}
      </div>
    </aside>
  );
}
