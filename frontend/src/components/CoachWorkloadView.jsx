import React, { useState } from 'react';
import { Clock, Users, Award, AlertTriangle, CheckCircle2, Search, BarChart2 } from 'lucide-react';

export default function CoachWorkloadView({ coachSummaries }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  if (!coachSummaries || coachSummaries.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p>No coach workload summary available. Please run the scheduling engine first.</p>
      </div>
    );
  }

  // Filter coach summaries
  const filteredSummaries = coachSummaries.filter(c => {
    const matchesSearch = c.coach_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.levels_taught.join(' ').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Global Statistics Calculations
  const totalCoaches = coachSummaries.length;
  const totalHours = coachSummaries.reduce((acc, c) => acc + c.total_hours, 0);
  const totalClasses = coachSummaries.reduce((acc, c) => acc + c.assigned_classes, 0);
  const avgUtilization = Math.round(
    coachSummaries.reduce((acc, c) => acc + c.utilization_pct, 0) / (totalCoaches || 1)
  );

  const underUtilizedCount = coachSummaries.filter(c => c.status === 'Under-Utilized').length;
  const optimalCount = coachSummaries.filter(c => c.status === 'Optimal').length;
  const exceededCount = coachSummaries.filter(c => c.status === 'Capacity Exceeded').length;

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            📊 Coach Workload & Teaching Hours Summary
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Comprehensive analysis of assigned classes, teaching hours, student reach, and capacity utilization per coach.
          </p>
        </div>

        {/* Global Metric Cards */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ background: 'var(--bg-secondary)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.7rem', color: '#d1d5db', display: 'block' }}>TOTAL COACHES</span>
            <strong style={{ fontSize: '1.2rem', color: '#fff' }}>{totalCoaches}</strong>
          </div>

          <div style={{ background: 'rgba(245, 158, 11, 0.15)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(245, 158, 11, 0.4)' }}>
            <span style={{ fontSize: '0.7rem', color: '#fde68a', display: 'block' }}>TOTAL ASSIGNED HOURS</span>
            <strong style={{ fontSize: '1.2rem', color: 'var(--accent-gold)' }}>{totalHours} hrs</strong>
          </div>

          <div style={{ background: 'rgba(59, 130, 246, 0.15)', padding: '10px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(59, 130, 246, 0.4)' }}>
            <span style={{ fontSize: '0.7rem', color: '#bfdbfe', display: 'block' }}>AVG CAPACITY UTILIZATION</span>
            <strong style={{ fontSize: '1.2rem', color: 'var(--accent-blue)' }}>{avgUtilization}%</strong>
          </div>
        </div>
      </div>

      {/* Controls: Search and Status Filter */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search coach name or level..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                padding: '8px 12px 8px 36px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                color: '#fff',
                fontSize: '0.85rem'
              }}
            />
          </div>

          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            style={{
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: '#fff',
              fontSize: '0.85rem'
            }}
          >
            <option value="ALL">All Utilization Statuses</option>
            <option value="Optimal">🟢 Optimal</option>
            <option value="Under-Utilized">🟡 Under-Utilized</option>
            <option value="Capacity Exceeded">🔴 Capacity Exceeded</option>
          </select>
        </div>

        {/* Quick Summary Badges */}
        <div style={{ display: 'flex', gap: '10px', fontSize: '0.775rem' }}>
          <span style={{ color: '#10b981', fontWeight: 600 }}>✓ Optimal: {optimalCount}</span>
          <span style={{ color: '#f59e0b', fontWeight: 600 }}>• Under-Utilized: {underUtilizedCount}</span>
          {exceededCount > 0 && <span style={{ color: '#ef4444', fontWeight: 600 }}>⚠ Exceeded: {exceededCount}</span>}
        </div>
      </div>

      {/* Main Coach Summary Table */}
      <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)' }}>
        <table className="custom-table">
          <thead>
            <tr>
              <th>Coach Name</th>
              <th>Assigned Classes</th>
              <th>Total Hours</th>
              <th>Students Coached</th>
              <th>Levels Handled</th>
              <th>Active Days</th>
              <th>Monthly Target Capacity</th>
              <th>Utilization Progress</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredSummaries.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '30px' }}>
                  No coach records match the filter criteria.
                </td>
              </tr>
            ) : (
              filteredSummaries.map(c => (
                <tr key={c.coach_name}>
                  <td>
                    <div style={{ fontWeight: 800, color: '#fff', fontSize: '0.95rem' }}>{c.coach_name}</div>
                  </td>
                  <td>
                    <span style={{ fontWeight: 800, color: 'var(--accent-gold)', fontSize: '1rem' }}>
                      {c.assigned_classes} classes
                    </span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 700, color: 'var(--accent-blue)', fontSize: '0.95rem' }}>
                      {c.total_hours} hrs
                    </span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 700, color: '#fff' }}>
                      {c.unique_students} students
                    </span>
                  </td>
                  <td style={{ maxWidth: '220px' }}>
                    <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', lineHeight: 1.3 }}>
                      {c.levels_taught.length > 0 ? c.levels_taught.join(', ') : 'None'}
                    </div>
                  </td>
                  <td>
                    <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)' }}>
                      {c.days_active.length > 0 ? c.days_active.join(', ') : 'None'}
                    </div>
                  </td>
                  <td>
                    <span style={{ fontWeight: 600, color: '#d1d5db' }}>
                      {c.monthly_capacity_min} – {c.monthly_capacity_max} max
                    </span>
                  </td>
                  <td style={{ minWidth: '150px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ flex: 1, height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${Math.min(c.utilization_pct, 100)}%`,
                          height: '100%',
                          background: c.status_color,
                          borderRadius: '4px'
                        }} />
                      </div>
                      <span style={{ fontSize: '0.775rem', fontWeight: 700, color: '#fff' }}>
                        {c.utilization_pct}%
                      </span>
                    </div>
                  </td>
                  <td>
                    <span className="badge" style={{ background: `${c.status_color}22`, border: `1px solid ${c.status_color}`, color: c.status_color, fontSize: '0.75rem', padding: '4px 10px' }}>
                      {c.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
