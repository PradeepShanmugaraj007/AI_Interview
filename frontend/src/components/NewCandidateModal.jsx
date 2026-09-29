import React, { useState } from 'react';
import { X, Upload, AlertCircle, CheckCircle2 } from 'lucide-react';
import { api } from '../api/client';

export default function NewCandidateModal({ isOpen, onClose, onSuccess }) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const defaultTimezone = typeof Intl !== 'undefined'
    ? Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Kolkata'
    : 'Asia/Kolkata';

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const formData = new FormData(e.target);
      const res = await api.createCandidate(formData);
      onSuccess(res);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save candidate.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Add Candidate & Intake Résumé</h3>
          <button className="modal-close" onClick={onClose} type="button">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  background: '#fef2f2',
                  border: '1px solid #fecaca',
                  color: '#991b1b',
                  padding: '10px 14px',
                  borderRadius: '6px',
                  fontSize: '13px',
                  marginBottom: '16px',
                }}
              >
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            <div className="form-grid">
              <div className="form-group">
                <label>Candidate Full Name *</label>
                <input
                  name="full_name"
                  type="text"
                  required
                  maxLength={120}
                  className="form-control"
                  placeholder="e.g. Priya Sharma"
                />
              </div>

              <div className="form-group">
                <label>Mobile Number (E.164) *</label>
                <input
                  name="phone"
                  type="tel"
                  required
                  className="form-control"
                  placeholder="+919876543210"
                />
              </div>
            </div>

            <div className="form-grid">
              <div className="form-group">
                <label>Role Title *</label>
                <input
                  name="job_title"
                  type="text"
                  required
                  maxLength={160}
                  className="form-control"
                  placeholder="e.g. Senior Backend Engineer"
                />
              </div>

              <div className="form-group">
                <label>Candidate Timezone *</label>
                <input
                  name="timezone"
                  type="text"
                  required
                  defaultValue={defaultTimezone}
                  className="form-control"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Email Address (Optional)</label>
              <input
                name="email"
                type="email"
                maxLength={254}
                className="form-control"
                placeholder="priya@example.com"
              />
            </div>

            <div className="form-group">
              <label>Role Requirements / Evaluation Rubric (Optional)</label>
              <textarea
                name="role_rubric"
                maxLength={6000}
                className="form-control"
                placeholder="Specify key technical skills, architectural depth, system design expectations, or problem-solving criteria."
              />
            </div>

            <div className="form-group">
              <label>Candidate Résumé (PDF, DOCX, TXT) *</label>
              <input
                name="resume"
                type="file"
                accept=".pdf,.docx,.txt"
                required
                className="form-control"
                style={{ padding: '6px 10px' }}
              />
            </div>

            <div style={{ marginTop: '14px', display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <input
                id="contact_consent"
                name="contact_consent"
                value="true"
                type="checkbox"
                required
                style={{ marginTop: '3px' }}
              />
              <label htmlFor="contact_consent" style={{ fontSize: '12px', color: '#475569', lineHeight: 1.4 }}>
                Candidate has provided affirmative consent to receive an automated AI screening call. Verbal consent is also re-verified on the phone.
              </label>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Parsing & Saving...' : 'Save Candidate'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
