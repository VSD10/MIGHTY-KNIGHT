import React, { useState } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  Layers,
  Users,
  Calendar,
  Clock,
  Award,
  Sparkles,
  AlertTriangle,
  ArrowRight,
  Info,
  Check,
  FileCheck,
  Target,
  Workflow,
  Cpu
} from 'lucide-react';

export default function SettingsView({ config }) {
  const [activeSection, setActiveSection] = useState('process');

  // 1. The 5 Core Dynamic Scheduling Stages
  const schedulingStages = [
    {
      number: '1',
      title: 'Generate Candidate Class Slots',
      badge: 'Template & Capacity Pool Generation',
      badgeColor: 'blue',
      summary: 'Builds candidate class opportunities across the monthly calendar from flexible batch templates and academy operating hours.',
      details: [
        {
          label: 'Flexible Capacity Pools',
          text: 'Master batches serve as reusable session templates (day of week, time slot, level) rather than locked student cohorts or fixed trainer ownership.'
        },
        {
          label: 'Operating Window Fallbacks',
          text: 'When demand for a specific student level exceeds batch templates, candidate slots are generated from academy weekday (06:00 AM – 10:00 PM) and Sunday operating hours.'
        },
        {
          label: 'Early Restriction Guards',
          text: 'Sunday sessions scheduled after 3:00 PM (15:00) are automatically excluded during slot generation.'
        }
      ]
    },
    {
      number: '2',
      title: 'Assign Students Toward Exact Monthly Quota',
      badge: 'Even Weekly Pacing',
      badgeColor: 'gold',
      summary: 'Distributes each student’s required classes evenly across the month to avoid early quota burnout and maintain consistent training habits.',
      details: [
        {
          label: 'Target Weekly Pacing',
          text: '16-class students are paced to ~4 classes/week; 8-class students to ~2 classes/week; 4-class students to ~1 class/week.'
        },
        {
          label: 'Daily Uniqueness Guarantee',
          text: 'Enforces at most 1 class per student per calendar date across the entire schedule (no same-day double booking).'
        },
        {
          label: 'Strict Quota Cap',
          text: 'Once a student reaches their monthly required_classes quota, no further sessions are scheduled.'
        }
      ]
    },
    {
      number: '3',
      title: 'Dynamic Qualified Trainer Selection',
      badge: 'Skill-Based Dispatch',
      badgeColor: 'green',
      summary: 'Selects any qualified, available trainer per session; trainer assignment is dynamic and determined by student level, availability, and workload limits.',
      details: [
        {
          label: 'Dynamic Trainer Assignment',
          text: 'Trainers are not permanently tied to specific students. Any coach qualified for the class level who is free and within their limits can teach.'
        },
        {
          label: 'Level Qualification Matrix',
          text: 'Trainers are strictly matched based on verified skill levels (e.g. Basic, Beginner, Early Intermediate, Intermediate).'
        },
        {
          label: 'Workload & Overlap Caps',
          text: 'Strictly enforces single occupancy (1 coach = 1 class at a time), day-of-week class caps, and monthly target capacity.'
        }
      ]
    },
    {
      number: '4',
      title: 'Controlled Deficit Catch-up Pass',
      badge: 'Quota Recovery',
      badgeColor: 'purple',
      summary: 'Enables students with remaining quota to safely catch up later in the month while adhering strictly to all hard rules.',
      details: [
        {
          label: 'Pacing Target Relaxation',
          text: 'If availability conflicts or missed slots caused a student to fall behind early in the month, weekly pacing targets are relaxed in later weeks.'
        },
        {
          label: 'Open Seat Prioritization',
          text: 'First attempts to place students with deficit into open seats in existing classes of matching level.'
        },
        {
          label: 'Supplemental Qualified Sessions',
          text: 'Provisions supplemental sessions only when qualified trainers are available without breaching daily or monthly workload limits.'
        }
      ]
    },
    {
      number: '5',
      title: 'Accountability & Root-Cause Diagnosis',
      badge: 'Zero-Loss Accounting',
      badgeColor: 'rose',
      summary: 'Verifies the zero-loss mathematical invariant for 100% of students and diagnoses the exact cause of any unassigned classes in Output 3.',
      details: [
        {
          label: 'Mathematical Invariant',
          text: 'Strictly enforces: Required Classes = Scheduled Classes + Remaining Deficit for every single enrolled student.'
        },
        {
          label: 'Output 3 Root-Cause Categorization',
          text: 'Unassigned classes are labeled with specific diagnostic causes: Trainer Capacity Exhausted, Student Level Unqualified, Sunday Tournament Restriction, or Restricted Availability.'
        },
        {
          label: 'Actionable Admin Guidance',
          text: 'Provides academy administrators with immediate recommendations to resolve deficits via manual edits or trainer adjustments.'
        }
      ]
    }
  ];

  // 2. Hard Rules (Enforced by Backend Engine)
  const hardRules = [
    {
      name: 'No Coach Overlap (Single Occupancy)',
      category: 'Trainer Feasibility',
      description: 'A trainer cannot be assigned to two classes occurring at the same time slot on the same date.',
      enforcement: 'Hard Feasibility Check & Manual Pre-Commit Guard'
    },
    {
      name: 'Student Daily Limit (Max 1 Class / Day)',
      category: 'Student Feasibility',
      description: 'A student can attend at most one class per calendar day across the entire monthly schedule.',
      enforcement: 'Hard Feasibility Check & Manual Pre-Commit Guard'
    },
    {
      name: 'Student Monthly Quota Cap',
      category: 'Quota Feasibility',
      description: 'Students are never scheduled beyond their enrolled monthly required_classes quota (e.g., 16, 8, or 4).',
      enforcement: 'Strict Allocation Ceiling'
    },
    {
      name: 'Trainer Level Qualification',
      category: 'Skill Feasibility',
      description: 'Trainers can only teach batches matching levels for which they are officially qualified in the capability matrix.',
      enforcement: 'Hard Capability Check'
    },
    {
      name: 'Day Availability Confirmation',
      category: 'Availability',
      description: 'Sessions are only scheduled on days when both the student and the trainer have explicitly confirmed availability.',
      enforcement: 'Schedule Day Match'
    },
    {
      name: 'Batch Capacity Maximum Ceilings',
      category: 'Room & Class Size',
      description: 'Group classes hold at most 10 students; Limited classes hold at most 4 students; Individual classes hold exactly 1 student.',
      enforcement: 'Hard Capacity Limit'
    },
    {
      name: 'Trainer Daily & Monthly Limits',
      category: 'Workload Feasibility',
      description: 'Trainers are strictly capped by day-of-week class limits (e.g., Mon–Fri max 4, Sat max 5, Sun max 2) and monthly maximum hours.',
      enforcement: 'Workload Guard'
    },
    {
      name: 'Sunday Tournament & Operating Ceiling',
      category: 'Sunday Policy',
      description: 'All Sunday sessions must end by 3:00 PM (15:00). Excludes designated tournament coaches (Dhaanush, Saravanan) and Intermediate levels.',
      enforcement: 'Time Window & Trainer Filter'
    },
    {
      name: 'Unified Server-Side Validation on Manual Edits',
      category: 'Manual Safety',
      description: 'All manual administrator operations (create, edit, delete, assign) validate the entire schedule state on the server before persisting.',
      enforcement: 'HTTP 400 Strict Rejection on Violation'
    }
  ];

  // 3. Soft Optimization Targets (Balanced via Deterministic Scoring)
  const softOptimizations = [
    {
      name: 'Even Weekly Pacing',
      category: 'Learning Rhythm',
      description: 'Aims to spread classes evenly throughout the month (~4/wk for 16, ~2/wk for 8, ~1/wk for 4), with controlled relaxation late in the month.',
      rationale: 'Avoids student fatigue while allowing catch-up if early classes are missed.'
    },
    {
      name: 'Group Batch Minimum of 4 Students',
      category: 'Batch Size Optimization',
      description: 'Group batches ideally have at least 4 students. If fewer compatible students exist, a soft warning is recorded, but students are never omitted.',
      rationale: 'Students are never left unscheduled simply because a compatible group has fewer than 4 students.'
    },
    {
      name: 'Preferred Time Slots & Recurring Days',
      category: 'Preference Matching',
      description: 'Prioritizes assigning students to their preferred morning, evening, or weekend time slots when multiple feasible options exist.',
      rationale: 'Improves attendance and student satisfaction.'
    },
    {
      name: 'Roster & Trainer Continuity',
      category: 'Continuity Preference',
      description: 'Favors assigning students who previously trained together or with the batch template’s preferred trainer when qualified.',
      rationale: 'Provides instructional consistency without creating rigid operational locks.'
    },
    {
      name: 'Trainer Workload Balancing',
      category: 'Fair Allocation',
      description: 'Balances session assignments among qualified coaches toward their individual monthly target workload minimums.',
      rationale: 'Prevents overloading single trainers while underutilizing other qualified staff.'
    }
  ];

  // Default coach priorities from config or fallback
  const coachPriorities = config?.coach_priority || {
    'Basic 1': ['Bathrinath', 'Abinaya', 'Manikandan', 'Prakash', 'Guruvanthana'],
    'Basic 2': ['Bathrinath', 'Abinaya', 'Manikandan', 'Prakash', 'Guruvanthana'],
    'Beginner 1': ['Bathrinath', 'Guruvanthana', 'Dhaanush', 'Manikandan', 'Abinaya', 'Prakash'],
    'Beginner 2': ['Guruvanthana', 'Dhaanush', 'Bathrinath', 'Prakash', 'Saravanan'],
    'Beginner 3': ['Guruvanthana', 'Dhaanush', 'Bathrinath', 'Prakash', 'Saravanan'],
    'Early Intermediate 1': ['Dhaanush', 'Saravanan', 'Arshath', 'Prakash', 'Guruvanthana'],
    'Early Intermediate 2': ['Dhaanush', 'Saravanan', 'Arshath', 'Prakash', 'Guruvanthana'],
    'Intermediate': ['Arshath', 'Dhaanush', 'Prakash', 'Saravanan']
  };

  const sundayRules = config?.sunday_rules || {
    max_end_time: '15:00',
    excluded_tournament_coaches: ['Dhaanush', 'Saravanan'],
    excluded_tournament_levels: ['Intermediate']
  };

  const weekdaySlots = config?.weekday_slots || [
    '06:00 AM – 07:00 AM', '07:00 AM – 08:00 AM', '09:00 AM – 10:00 AM',
    '10:00 AM – 11:00 AM', '11:00 AM – 12:00 PM', '12:00 PM – 01:00 PM',
    '01:00 PM – 02:00 PM', '04:00 PM – 05:00 PM', '05:00 PM – 06:00 PM',
    '06:00 PM – 07:00 PM', '07:00 PM – 08:00 PM', '08:00 PM – 09:00 PM',
    '09:00 PM – 10:00 PM'
  ];

  const sundaySlots = config?.sunday_slots || [
    '09:00 AM – 10:00 AM', '10:00 AM – 11:00 AM', '11:00 AM – 12:00 PM',
    '12:00 PM – 01:00 PM', '01:00 PM – 02:00 PM', '02:00 PM – 03:00 PM'
  ];

  return (
    <div className="glass-panel" style={{ padding: '28px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* 1. Top Header Banner */}
      <div style={{ marginBottom: '22px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 900, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '10px', margin: 0 }}>
              <Cpu size={26} style={{ color: 'var(--accent-gold)' }} />
              Scheduling Engine Architecture & Operational Rules
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px', marginBottom: 0 }}>
              Truthful architectural overview of the dynamic monthly scheduling engine, execution pipeline, and constraint hierarchy.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <span className="badge badge-gold" style={{ fontSize: '0.75rem', padding: '5px 12px' }}>
              Deterministic Optimization
            </span>
            <span className="badge badge-success" style={{ fontSize: '0.75rem', padding: '5px 12px' }}>
              Zero-Loss Accounting
            </span>
          </div>
        </div>
      </div>

      {/* 2. Core Architectural Model Statement */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(30, 58, 138, 0.45) 0%, rgba(15, 23, 42, 0.75) 100%)',
        border: '1px solid rgba(59, 130, 246, 0.4)',
        borderRadius: 'var(--radius-md)',
        padding: '20px 24px',
        marginBottom: '26px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '16px'
      }}>
        <div style={{
          width: '46px',
          height: '46px',
          borderRadius: '12px',
          background: 'rgba(59, 130, 246, 0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          marginTop: '2px'
        }}>
          <Sparkles size={24} style={{ color: '#60a5fa' }} />
        </div>
        <div>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#ffffff', marginBottom: '6px' }}>
            Core Operational Model: Dynamic Monthly Quota Scheduling with Capacity Pools
          </h3>
          <p style={{ fontSize: '0.85rem', color: '#bfdbfe', margin: 0, lineHeight: 1.6 }}>
            The Mighty Knight scheduler assigns students to class sessions dynamically based on their individual monthly enrolled quotas. Master batches are treated as <strong>flexible capacity pools and session templates</strong> (defining recurring days, times, and levels), <strong>not permanent trainer-student ownership or locked cohorts</strong>. Qualified trainers are dynamically selected per session to maximize fulfilled quotas and avoid trainer burnout.
          </p>
        </div>
      </div>

      {/* 3. Navigation Sub-Tabs */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', flexWrap: 'wrap' }}>
        <button
          onClick={() => setActiveSection('process')}
          style={{
            background: activeSection === 'process' ? 'var(--accent-gold)' : 'var(--bg-card)',
            color: activeSection === 'process' ? '#000' : 'var(--text-primary)',
            border: '1px solid ' + (activeSection === 'process' ? 'var(--accent-gold)' : 'var(--border-color)'),
            borderRadius: 'var(--radius-sm)',
            padding: '8px 16px',
            fontSize: '0.825rem',
            fontWeight: 800,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s ease'
          }}
        >
          <Workflow size={16} /> 1. The 5-Stage Scheduling Process
        </button>

        <button
          onClick={() => setActiveSection('rules')}
          style={{
            background: activeSection === 'rules' ? 'var(--accent-gold)' : 'var(--bg-card)',
            color: activeSection === 'rules' ? '#000' : 'var(--text-primary)',
            border: '1px solid ' + (activeSection === 'rules' ? 'var(--accent-gold)' : 'var(--border-color)'),
            borderRadius: 'var(--radius-sm)',
            padding: '8px 16px',
            fontSize: '0.825rem',
            fontWeight: 800,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s ease'
          }}
        >
          <ShieldCheck size={16} /> 2. Hard Rules vs. Soft Optimization
        </button>

        <button
          onClick={() => setActiveSection('trainers')}
          style={{
            background: activeSection === 'trainers' ? 'var(--accent-gold)' : 'var(--bg-card)',
            color: activeSection === 'trainers' ? '#000' : 'var(--text-primary)',
            border: '1px solid ' + (activeSection === 'trainers' ? 'var(--accent-gold)' : 'var(--border-color)'),
            borderRadius: 'var(--radius-sm)',
            padding: '8px 16px',
            fontSize: '0.825rem',
            fontWeight: 800,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s ease'
          }}
        >
          <Users size={16} /> 3. Trainer Qualification Matrix
        </button>

        <button
          onClick={() => setActiveSection('windows')}
          style={{
            background: activeSection === 'windows' ? 'var(--accent-gold)' : 'var(--bg-card)',
            color: activeSection === 'windows' ? '#000' : 'var(--text-primary)',
            border: '1px solid ' + (activeSection === 'windows' ? 'var(--accent-gold)' : 'var(--border-color)'),
            borderRadius: 'var(--radius-sm)',
            padding: '8px 16px',
            fontSize: '0.825rem',
            fontWeight: 800,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s ease'
          }}
        >
          <Clock size={16} /> 4. Operating Hours & Capacities
        </button>
      </div>

      {/* SECTION 1: THE 5-STAGE PROCESS */}
      {activeSection === 'process' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{
            background: 'var(--bg-secondary)',
            padding: '16px 20px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            marginBottom: '4px'
          }}>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#ffffff', margin: 0, marginBottom: '6px' }}>
              Deterministic Monthly Execution Pipeline
            </h4>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
              When you click <strong>Run Engine</strong>, the system executes a 5-stage deterministic workflow. Every assignment is governed by mathematical feasibility and fairness scoring, ensuring that low-quota students are never starved of capacity by high-quota students.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {schedulingStages.map((st) => (
              <div
                key={st.number}
                style={{
                  background: 'var(--bg-card)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                  padding: '22px',
                  boxShadow: 'var(--shadow-sm)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '50%',
                      background: 'rgba(250, 204, 21, 0.15)',
                      border: '1px solid var(--accent-gold)',
                      color: 'var(--accent-gold)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 900,
                      fontSize: '1rem'
                    }}>
                      {st.number}
                    </div>
                    <div>
                      <h4 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#ffffff', margin: 0 }}>
                        Stage {st.number}: {st.title}
                      </h4>
                    </div>
                  </div>
                  <span className="badge badge-gold" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                    {st.badge}
                  </span>
                </div>

                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '16px', lineHeight: 1.5 }}>
                  {st.summary}
                </p>

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: '12px',
                  background: 'rgba(0, 0, 0, 0.25)',
                  padding: '16px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid rgba(255, 255, 255, 0.05)'
                }}>
                  {st.details.map((item, idx) => (
                    <div key={idx}>
                      <span style={{ fontSize: '0.725rem', fontWeight: 800, color: 'var(--accent-gold)', display: 'block', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '3px' }}>
                        {item.label}
                      </span>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
                        {item.text}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 2: HARD RULES VS SOFT OPTIMIZATION */}
      {activeSection === 'rules' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Hard Constraints Card */}
          <div style={{
            background: 'var(--bg-card)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            padding: '24px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <CheckCircle2 size={18} style={{ color: '#10b981' }} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#ffffff', margin: 0 }}>
                  Hard Feasibility Constraints (100% Enforced)
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#6ee7b7' }}>
                  Non-negotiable invariants. The engine will NEVER schedule a session or allow a manual edit that violates any of these conditions.
                </span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px', marginTop: '16px' }}>
              {hardRules.map((rule, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '14px 16px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '6px' }}>
                      <strong style={{ fontSize: '0.875rem', color: '#ffffff' }}>
                        {rule.name}
                      </strong>
                      <span className="badge badge-success" style={{ fontSize: '0.65rem', whiteSpace: 'nowrap' }}>
                        {rule.category}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: 0, lineHeight: 1.45 }}>
                      {rule.description}
                    </p>
                  </div>
                  <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.06)', fontSize: '0.725rem', color: 'var(--accent-gold)', fontWeight: 700 }}>
                    Enforcement: {rule.enforcement}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Soft Optimization Card */}
          <div style={{
            background: 'var(--bg-card)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid rgba(250, 204, 21, 0.35)',
            padding: '24px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(250, 204, 21, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Sparkles size={18} style={{ color: 'var(--accent-gold)' }} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#ffffff', margin: 0 }}>
                  Soft Optimization Targets (Best-Effort Trade-offs)
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#fde68a' }}>
                  Optimization objectives balanced through deterministic priority scoring. Relaxation is permitted to maximize completed quotas.
                </span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px', marginTop: '16px' }}>
              {softOptimizations.map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '14px 16px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '6px' }}>
                      <strong style={{ fontSize: '0.875rem', color: '#ffffff' }}>
                        {item.name}
                      </strong>
                      <span className="badge badge-gold" style={{ fontSize: '0.65rem', whiteSpace: 'nowrap' }}>
                        {item.category}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.8rem', color: '#cbd5e1', margin: 0, lineHeight: 1.45 }}>
                      {item.description}
                    </p>
                  </div>
                  <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.06)', fontSize: '0.725rem', color: '#94a3b8' }}>
                    <span style={{ color: '#fbbf24', fontWeight: 700 }}>Operational Rationale:</span> {item.rationale}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SECTION 3: TRAINER QUALIFICATION MATRIX */}
      {activeSection === 'trainers' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{
            background: 'var(--bg-secondary)',
            padding: '16px 20px',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)'
          }}>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#ffffff', margin: 0, marginBottom: '6px' }}>
              Level-Wise Trainer Qualification & Priority Ranking
            </h4>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
              The scheduler routes student levels strictly to qualified trainers ordered by priority. Trainers appearing first are selected as primary coaches, while subsequent trainers serve as qualified substitutes when the primary coach has reached their daily limit or is unavailable.
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '16px'
          }}>
            {Object.entries(coachPriorities).map(([level, coaches]) => (
              <div
                key={level}
                style={{
                  background: 'var(--bg-card)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                  padding: '18px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '8px' }}>
                  <h4 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--accent-gold)', margin: 0 }}>
                    {level}
                  </h4>
                  <span className="badge badge-gold" style={{ fontSize: '0.65rem' }}>
                    {coaches.length} Qualified Coaches
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {coaches.map((cName, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        background: idx === 0 ? 'rgba(250, 204, 21, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                        border: idx === 0 ? '1px solid rgba(250, 204, 21, 0.25)' : '1px solid transparent',
                        fontSize: '0.825rem'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{
                          width: '20px',
                          height: '20px',
                          borderRadius: '50%',
                          background: idx === 0 ? 'var(--accent-gold)' : 'rgba(255, 255, 255, 0.1)',
                          color: idx === 0 ? '#000' : 'var(--text-secondary)',
                          fontSize: '0.7rem',
                          fontWeight: 800,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}>
                          {idx + 1}
                        </span>
                        <span style={{ fontWeight: idx === 0 ? 700 : 500, color: idx === 0 ? '#fff' : '#cbd5e1' }}>
                          {cName}
                        </span>
                      </div>
                      <span style={{ fontSize: '0.7rem', color: idx === 0 ? 'var(--accent-gold)' : 'var(--text-muted)' }}>
                        {idx === 0 ? 'Primary' : `Priority ${idx + 1}`}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 4: OPERATING HOURS & CAPACITIES */}
      {activeSection === 'windows' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Batch Type Capacities */}
          <div style={{
            background: 'var(--bg-card)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            padding: '22px'
          }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 800, color: '#ffffff', marginBottom: '14px' }}>
              Batch Type Capacity Definitions
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
              <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <strong style={{ fontSize: '0.95rem', color: '#fff' }}>Group Batch (G)</strong>
                  <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>Max 10 Students</span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
                  Hard maximum of 10 students. Minimum capacity target is 4 students; if fewer students are available, a soft notice is raised without omitting any enrolled students.
                </p>
              </div>

              <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <strong style={{ fontSize: '0.95rem', color: '#fff' }}>Limited Students Batch (L)</strong>
                  <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>1 – 4 Students</span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
                  Intensive format restricted to 1 to 4 students. Hard ceiling of 4 students is strictly enforced across automated and manual assignments.
                </p>
              </div>

              <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <strong style={{ fontSize: '0.95rem', color: '#fff' }}>Individual Batch (I)</strong>
                  <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>Exactly 1 Student</span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
                  Dedicated 1-on-1 private instruction. Exactly 1 student per session; never combined with other students.
                </p>
              </div>
            </div>
          </div>

          {/* Sunday Tournament Rules */}
          <div style={{
            background: 'var(--bg-card)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            padding: '22px'
          }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 800, color: '#ffffff', marginBottom: '8px' }}>
              Sunday Operating Policy & Tournament Restrictions
            </h4>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Academy policies strictly limit Sunday sessions to reserve coaches and resources for weekly academy tournaments.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px' }}>
              <div style={{ background: 'var(--bg-secondary)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', fontWeight: 700 }}>SUNDAY OPERATING CEILING</span>
                <strong style={{ fontSize: '1.05rem', color: '#f59e0b' }}>3:00 PM (15:00) Strict Limit</strong>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px', margin: 0 }}>
                  No classes can start or end after 3:00 PM on Sundays.
                </p>
              </div>

              <div style={{ background: 'var(--bg-secondary)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', fontWeight: 700 }}>TOURNAMENT COACH EXCLUSIONS</span>
                <strong style={{ fontSize: '0.95rem', color: '#fff' }}>
                  {sundayRules.excluded_tournament_coaches?.join(', ') || 'Dhaanush, Saravanan'}
                </strong>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px', margin: 0 }}>
                  Excluded from Sunday regular classes to arbitrate tournament matches.
                </p>
              </div>

              <div style={{ background: 'var(--bg-secondary)', padding: '14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', fontWeight: 700 }}>TOURNAMENT LEVEL EXCLUSIONS</span>
                <strong style={{ fontSize: '0.95rem', color: '#fff' }}>
                  {sundayRules.excluded_tournament_levels?.join(', ') || 'Intermediate'}
                </strong>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px', margin: 0 }}>
                  Intermediate students participate in tournament play rather than routine classes on Sundays.
                </p>
              </div>
            </div>
          </div>

          {/* Operating Time Slots */}
          <div style={{
            background: 'var(--bg-card)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            padding: '22px'
          }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 800, color: '#ffffff', marginBottom: '14px' }}>
              Academy Operating Slot Windows
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
              <div>
                <span style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--accent-gold)', display: 'block', marginBottom: '10px' }}>
                  Weekday Slots (Mon – Sat: 06:00 AM – 10:00 PM) · {weekdaySlots.length} Windows
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {weekdaySlots.map((s, idx) => (
                    <span
                      key={idx}
                      style={{
                        fontSize: '0.75rem',
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        color: '#cbd5e1'
                      }}
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <span style={{ fontSize: '0.8rem', fontWeight: 800, color: '#f59e0b', display: 'block', marginBottom: '10px' }}>
                  Sunday Slots (09:00 AM – 03:00 PM) · {sundaySlots.length} Windows
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {sundaySlots.map((s, idx) => (
                    <span
                      key={idx}
                      style={{
                        fontSize: '0.75rem',
                        background: 'rgba(245, 158, 11, 0.1)',
                        border: '1px solid rgba(245, 158, 11, 0.25)',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        color: '#fde68a'
                      }}
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
