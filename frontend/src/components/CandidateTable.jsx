import React, { useState } from 'react';
import { Search, Phone, PhoneOff, FileText, CheckCircle2, AlertCircle, Clock, Plus, ExternalLink } from 'lucide-react';

export default function CandidateTable({
  candidates,
  onOpenIntake,
  onViewScorecard,
  onTriggerCall,
  onHangupCall,
  callingId,
}) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('ALL');

  const filtered = (candidates || []).filter((c) => {
    const matchesSearch =
      (c.full_name || '').toLowerCase().includes(search.toLowerCase()) ||
      (c.job_title || '').toLowerCase().includes(search.toLowerCase()) ||
      (c.email || '').toLowerCase().includes(search.toLowerCase()) ||
      (c.phone_last_four || '').includes(search);

    if (!matchesSearch) return false;

    const rec = c.latest_interview?.recommendation;
    const status = c.latest_interview?.status;

    if (filter === 'SHORTLISTED') return rec === 'recommend_human_shortlist_review';
    if (filter === 'REVIEW') return rec === 'recommend_human_review_before_rejecting';
    if (filter === 'IN_PROGRESS') return status === 'in_progress' || callingId === c.id;
    if (filter === 'READY') return !c.latest_interview;

    return true;
  });

  const getStatusBadge = (c) => {
    const status = c.latest_interview?.status;
    const rec = c.latest_interview?.recommendation;

    if (callingId === c.id || status === 'in_progress') {
      return (
        <span className="badge badge-amber">
          <Clock size={11} className="spin-icon" /> Calling...
        </span>
      );
    }

    if (status === 'no_answer') {
      return (
        <span className="badge badge-amber">
          <PhoneOff size={11} /> No Answer
        </span>
      );
    }

    if (status === 'busy') {
      return (
        <span className="badge badge-amber">
          <AlertCircle size={11} /> Line Busy
        </span>
      );
    }

    if (rec === 'recommend_human_shortlist_review') {
      return (
        <span className="badge badge-green">
          <CheckCircle2 size={11} /> Shortlisted
        </span>
      );
    }
    if (rec === 'recommend_human_review_before_rejecting') {
      return (
        <span className="badge badge-blue">
          <AlertCircle size={11} /> Review Needed
        </span>
      );
    }
    if (status === 'completed') {
      const isEarly = rec && (rec.includes('hung up') || rec.includes('terminated') || rec.includes('ended'));
      return (
        <span className="badge badge-gray">
          {isEarly ? 'Call Ended' : 'Completed'}
        </span>
      );
    }
    return <span className="badge badge-gray">Ready to Call</span>;
  };

  return (
    <div>
      <div className="action-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="search-box">
            <Search size={15} color="#94a3b8" />
            <input
              type="text"
              placeholder="Search candidate, role, phone..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '6px' }}>
            {['ALL', 'SHORTLISTED', 'REVIEW', 'IN_PROGRESS', 'READY'].map((tab) => (
              <button
                key={tab}
                className={`btn btn-sm ${filter === tab ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setFilter(tab)}
              >
                {tab === 'ALL' ? 'All' : tab.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        <div className="action-buttons">
          <button className="btn btn-primary" onClick={onOpenIntake}>
            <Plus size={15} />
            <span>Add Candidate</span>
          </button>
        </div>
      </div>

      <div className="table-card">
        <table className="crm-table">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Applied Role</th>
              <th>Phone</th>
              <th>Timezone</th>
              <th>Status</th>
              <th>Score</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '48px 20px', color: '#64748b' }}>
                  No candidates match your current search or filter.
                </td>
              </tr>
            ) : (
              filtered.map((c) => {
                const score = c.latest_interview?.score;
                const hasInterview = Boolean(c.latest_interview);
                const isDialling = callingId === c.id;

                return (
                  <tr key={c.id}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{c.full_name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {c.email || c.resume_filename || 'No email provided'}
                      </div>
                    </td>
                    <td>
                      <div style={{ fontWeight: 500 }}>{c.job_title}</div>
                    </td>
                    <td style={{ fontVariantNumeric: 'tabular-nums' }}>
                      <span style={{ color: 'var(--text-muted)' }}>•••• </span>
                      {c.phone_last_four}
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                      {c.timezone}
                    </td>
                    <td>{getStatusBadge(c)}</td>
                    <td>
                      {typeof score === 'number' ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, fontSize: '13px', fontVariantNumeric: 'tabular-nums' }}>
                            {score}%
                          </span>
                          <div
                            style={{
                              width: '48px',
                              height: '5px',
                              background: '#e2e8f0',
                              borderRadius: '3px',
                              overflow: 'hidden',
                            }}
                          >
                            <div
                              style={{
                                width: `${Math.min(100, Math.max(0, score))}%`,
                                height: '100%',
                                background: score >= 70 ? '#10b981' : '#3b82f6',
                              }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-dim)', fontSize: '12px' }}>—</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        {hasInterview && (
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => onViewScorecard(c.latest_interview.id)}
                            title="View Scorecard & Transcript"
                          >
                            <FileText size={13} />
                            <span>Scorecard</span>
                          </button>
                        )}
                        {isDialling || c.latest_interview?.status === 'in_progress' ? (
                          <button
                            className="btn btn-sm"
                            style={{
                              background: '#ef4444',
                              color: '#ffffff',
                              border: '1px solid #dc2626',
                              fontWeight: 600,
                            }}
                            onClick={() => onHangupCall(c.id)}
                            title="Cut / End call immediately"
                          >
                            <PhoneOff size={13} />
                            <span>End Call</span>
                          </button>
                        ) : (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => onTriggerCall(c.id)}
                            title="Place live outbound interview call"
                          >
                            <Phone size={13} />
                            <span>Call</span>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
