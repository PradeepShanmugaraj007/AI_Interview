import React, { useState, useEffect, useCallback } from 'react';
import TopNav from './components/TopNav';
import MetricCards from './components/MetricCards';
import CandidateTable from './components/CandidateTable';
import NewCandidateModal from './components/NewCandidateModal';
import ScorecardDrawer from './components/ScorecardDrawer';
import { api } from './api/client';
import { AlertCircle, CheckCircle2, PhoneCall } from 'lucide-react';

export default function App() {
  const [stats, setStats] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [callingId, setCallingId] = useState(null);

  // Modals & Drawers
  const [isIntakeOpen, setIsIntakeOpen] = useState(false);
  const [selectedInterview, setSelectedInterview] = useState(null);
  const [isScorecardOpen, setIsScorecardOpen] = useState(false);

  // Notification Toast
  const [notification, setNotification] = useState(null);

  const showNotification = (type, message) => {
    setNotification({ type, message });
    setTimeout(() => {
      setNotification(null);
    }, 5000);
  };

  const loadData = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    try {
      const [statsData, candidatesData, healthData] = await Promise.all([
        api.getStats().catch(() => null),
        api.getCandidates().catch(() => []),
        api.getHealth().catch(() => null),
      ]);
      if (statsData) setStats(statsData);
      if (candidatesData) {
        setCandidates(candidatesData);
        // Automatically clear callingId if candidate call is no longer in progress
        setCallingId((prev) => {
          if (!prev) return null;
          const candidate = candidatesData.find((c) => c.id === prev);
          return candidate?.latest_interview?.status === 'in_progress' ? prev : null;
        });
      }
      if (healthData) setHealth(healthData);
    } catch (err) {
      console.error('Failed to load CRM data:', err);
    } finally {
      if (!isSilent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Polling loop: If any call is in progress or callingId is active, poll every 3s
  useEffect(() => {
    const hasActiveCall = callingId || (candidates || []).some(
      (c) => c.latest_interview?.status === 'in_progress'
    );

    const intervalTime = hasActiveCall ? 2500 : 10000;
    const interval = setInterval(() => {
      loadData(true);
    }, intervalTime);

    return () => clearInterval(interval);
  }, [callingId, candidates, loadData]);

  // Handle triggering an outbound call
  const handleTriggerCall = async (candidateId) => {
    setCallingId(candidateId);
    showNotification('info', 'Preparing question plan and dialing candidate phone...');
    try {
      const interview = await api.triggerCall(candidateId);
      showNotification('success', `Call initiated! Call SID: ${interview.call_sid || interview.id}`);
      await loadData(true);
    } catch (err) {
      showNotification('error', err.message || 'Call could not be placed.');
      setCallingId(null);
    }
  };

  // Handle cutting / terminating call from recruiter side
  const handleHangupCall = async (candidateId) => {
    showNotification('info', 'Terminating phone call...');
    try {
      await api.hangupCall(candidateId);
      showNotification('success', 'Call terminated.');
      setCallingId(null);
      await loadData(true);
    } catch (err) {
      showNotification('error', err.message || 'Failed to terminate call.');
    }
  };

  // Handle viewing scorecard
  const handleViewScorecard = async (interviewId) => {
    try {
      const interviewData = await api.getInterview(interviewId);
      setSelectedInterview(interviewData);
      setIsScorecardOpen(true);
    } catch (err) {
      showNotification('error', err.message || 'Could not load interview scorecard.');
    }
  };

  return (
    <>
      <TopNav health={health} onRefresh={() => loadData(false)} loading={loading} />

      <main className="crm-container">
        {/* Banner Notifications */}
        {notification && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '10px',
              padding: '12px 18px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 500,
              marginBottom: '16px',
              background:
                notification.type === 'error'
                  ? '#fef2f2'
                  : notification.type === 'success'
                  ? '#ecfdf5'
                  : '#eff6ff',
              color:
                notification.type === 'error'
                  ? '#991b1b'
                  : notification.type === 'success'
                  ? '#065f46'
                  : '#1e40af',
              border: `1px solid ${
                notification.type === 'error'
                  ? '#fecaca'
                  : notification.type === 'success'
                  ? '#a7f3d0'
                  : '#bfdbfe'
              }`,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {notification.type === 'error' ? (
                <AlertCircle size={16} />
              ) : notification.type === 'success' ? (
                <CheckCircle2 size={16} />
              ) : (
                <PhoneCall size={16} className="spin-icon" />
              )}
              <span>{notification.message}</span>
            </div>
            <button
              onClick={() => setNotification(null)}
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                fontSize: '14px',
                color: 'inherit',
              }}
            >
              ✕
            </button>
          </div>
        )}

        {/* Aggregated Pipeline Metrics */}
        <MetricCards stats={stats} />

        {/* Candidate List & Actions */}
        <CandidateTable
          candidates={candidates}
          onOpenIntake={() => setIsIntakeOpen(true)}
          onViewScorecard={handleViewScorecard}
          onTriggerCall={handleTriggerCall}
          onHangupCall={handleHangupCall}
          callingId={callingId}
        />
      </main>

      {/* Intake Modal */}
      <NewCandidateModal
        isOpen={isIntakeOpen}
        onClose={() => setIsIntakeOpen(false)}
        onSuccess={(newCandidate) => {
          showNotification('success', `Candidate ${newCandidate.full_name} saved!`);
          loadData(true);
        }}
      />

      {/* Scorecard Slide-Over Drawer */}
      <ScorecardDrawer
        interview={selectedInterview}
        isOpen={isScorecardOpen}
        onClose={() => {
          setIsScorecardOpen(false);
          setSelectedInterview(null);
        }}
      />
    </>
  );
}
