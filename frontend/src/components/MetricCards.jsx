import React from 'react';
import { Users, PhoneCall, Award, TrendingUp } from 'lucide-react';

export default function MetricCards({ stats }) {
  const data = stats || {
    total_candidates: 0,
    completed_interviews: 0,
    shortlisted_count: 0,
    shortlist_rate: 0,
    average_score: 0,
  };

  return (
    <div className="stats-grid">
      <div className="stat-card">
        <div className="stat-card-label">
          <span>Total Candidates</span>
          <Users size={16} color="#64748b" />
        </div>
        <div className="stat-card-value">{data.total_candidates}</div>
        <div className="stat-card-helper">Résumés parsed & consented</div>
      </div>

      <div className="stat-card">
        <div className="stat-card-label">
          <span>Completed Calls</span>
          <PhoneCall size={16} color="#64748b" />
        </div>
        <div className="stat-card-value">{data.completed_interviews}</div>
        <div className="stat-card-helper">
          {data.in_progress_interviews ? `${data.in_progress_interviews} active right now` : '100% transcript coverage'}
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-card-label">
          <span>Shortlist Rate</span>
          <Award size={16} color="#059669" />
        </div>
        <div className="stat-card-value" style={{ color: '#065f46' }}>
          {data.shortlist_rate}%
        </div>
        <div className="stat-card-helper">{data.shortlisted_count} candidate(s) meet rubric</div>
      </div>

      <div className="stat-card">
        <div className="stat-card-label">
          <span>Avg Rubric Score</span>
          <TrendingUp size={16} color="#2563eb" />
        </div>
        <div className="stat-card-value" style={{ color: '#1e40af' }}>
          {data.average_score}%
        </div>
        <div className="stat-card-helper">Weighted 0-4 point evaluation</div>
      </div>
    </div>
  );
}
