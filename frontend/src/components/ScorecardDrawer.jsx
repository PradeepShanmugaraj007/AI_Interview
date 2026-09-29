import React, { useState } from 'react';
import { X, CheckCircle2, AlertTriangle, FileText, MessageSquare, Award, Clock } from 'lucide-react';

export default function ScorecardDrawer({ interview, isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('RUBRIC');

  if (!isOpen || !interview) return null;

  const result = interview.result || {};
  const plan = interview.plan || {};
  const candidate = interview.candidate || {};
  const questions = plan.questions || [];
  const answers = result.answers || [];
  const transcriptTurns = result.transcript || [];

  // Match answer score to question id
  const answerByQuestion = {};
  answers.forEach((ans) => {
    answerByQuestion[ans.question_id] = ans;
  });

  const isShortlist = result.recommendation === 'recommend_human_shortlist_review';
  const isReview = result.recommendation === 'recommend_human_review_before_rejecting';

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        {/* Drawer Header */}
        <div className="modal-header" style={{ padding: '20px 28px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>
                {candidate.full_name || 'Interview Review'}
              </h2>
              <span className={`badge ${interview.status === 'completed' ? 'badge-green' : 'badge-amber'}`}>
                {interview.status}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              {candidate.job_title} · Mobile ending {candidate.phone_last_four || '••••'} · {candidate.timezone}
            </div>
          </div>

          <button className="modal-close" onClick={onClose} type="button">
            <X size={20} />
          </button>
        </div>

        {/* Overall Recommendation Summary Banner */}
        <div style={{ padding: '16px 28px', background: '#f8fafc', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div
                style={{
                  fontSize: '32px',
                  fontWeight: 800,
                  fontVariantNumeric: 'tabular-nums',
                  color: isShortlist ? '#065f46' : isReview ? '#1e40af' : '#0f172a',
                }}
              >
                {typeof result.overall_score === 'number' ? `${result.overall_score}%` : '—'}
              </div>

              <div>
                <div style={{ fontSize: '13px', fontWeight: 700 }}>
                  {isShortlist
                    ? 'Recommend Human Shortlist Review'
                    : isReview
                    ? 'Recommend Review Before Rejecting'
                    : 'Awaiting Final Evaluation'}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {answers.length} of {questions.length} questions answered · Completed{' '}
                  {interview.completed_at ? new Date(interview.completed_at).toLocaleTimeString() : 'in progress'}
                </div>
              </div>
            </div>

            {/* Tab Switcher */}
            <div style={{ display: 'flex', gap: '4px', background: '#e2e8f0', padding: '3px', borderRadius: '6px' }}>
              <button
                className={`btn btn-sm ${activeTab === 'RUBRIC' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ border: 'none', padding: '4px 10px' }}
                onClick={() => setActiveTab('RUBRIC')}
              >
                <Award size={12} /> Rubric & Answers
              </button>
              <button
                className={`btn btn-sm ${activeTab === 'TRANSCRIPT' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ border: 'none', padding: '4px 10px' }}
                onClick={() => setActiveTab('TRANSCRIPT')}
              >
                <MessageSquare size={12} /> Full Transcript
              </button>
            </div>
          </div>
        </div>

        {/* Drawer Scrollable Body */}
        <div style={{ padding: '24px 28px', overflowY: 'auto', flex: 1 }}>
          {activeTab === 'RUBRIC' ? (
            <div style={{ display: 'grid', gap: '18px' }}>
              {questions.length === 0 ? (
                <div style={{ color: '#64748b', textAlign: 'center', padding: '32px 0' }}>
                  No question plan recorded for this interview.
                </div>
              ) : (
                questions.map((q, idx) => {
                  const ans = answerByQuestion[q.question_id];
                  const score = ans ? ans.score : null;

                  return (
                    <div
                      key={q.question_id || idx}
                      style={{
                        background: '#ffffff',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '16px 18px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                            Question {idx + 1} · {q.competency || 'Evaluation'}
                          </div>
                          <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginTop: '4px' }}>
                            {q.prompt}
                          </div>
                        </div>

                        <div
                          style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            fontWeight: 700,
                            fontSize: '13px',
                            background: score !== null && score >= 3 ? '#ecfdf5' : score !== null && score >= 2 ? '#eff6ff' : '#f8fafc',
                            color: score !== null && score >= 3 ? '#065f46' : score !== null && score >= 2 ? '#1e40af' : '#64748b',
                            border: '1px solid var(--border-subtle)',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {score !== null ? `${score} / 4 pts` : 'Pending'}
                        </div>
                      </div>

                      {ans && (
                        <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
                          {ans.evidence_quote && (
                            <div style={{ marginBottom: '8px' }}>
                              <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748b' }}>CANDIDATE QUOTE (EVIDENCE):</div>
                              <blockquote
                                style={{
                                  margin: '4px 0 0 0',
                                  paddingLeft: '10px',
                                  borderLeft: '3px solid #3b82f6',
                                  fontStyle: 'italic',
                                  fontSize: '13px',
                                  color: '#334155',
                                }}
                              >
                                "{ans.evidence_quote}"
                              </blockquote>
                            </div>
                          )}

                          {ans.rationale && (
                            <div style={{ marginTop: '6px' }}>
                              <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748b' }}>EVALUATOR RATIONALE:</div>
                              <p style={{ margin: '3px 0 0 0', fontSize: '12.5px', color: '#475569' }}>
                                {ans.rationale}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '14px' }}>
              {transcriptTurns.length === 0 ? (
                <div style={{ color: '#64748b', textAlign: 'center', padding: '32px 0' }}>
                  No conversational transcript recorded yet.
                </div>
              ) : (
                transcriptTurns.map((turn, idx) => {
                  const isCandidate = turn.speaker === 'candidate';
                  return (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: isCandidate ? 'flex-end' : 'flex-start',
                      }}
                    >
                      <div
                        style={{
                          fontSize: '11px',
                          color: '#64748b',
                          marginBottom: '3px',
                          padding: '0 4px',
                        }}
                      >
                        {isCandidate ? candidate.full_name || 'Candidate' : 'AI Interviewer'}
                      </div>
                      <div
                        style={{
                          maxWidth: '82%',
                          background: isCandidate ? '#0f172a' : '#f1f5f9',
                          color: isCandidate ? '#ffffff' : '#0f172a',
                          padding: '10px 14px',
                          borderRadius: '8px',
                          fontSize: '13px',
                          lineHeight: 1.45,
                        }}
                      >
                        {turn.text}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
