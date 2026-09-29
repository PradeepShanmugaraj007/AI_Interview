import React from 'react';
import { PhoneCall, RefreshCw, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function TopNav({ health, onRefresh, loading }) {
  const isReady = health && (!health.missing_env || health.missing_env.length === 0);

  return (
    <header className="crm-header">
      <div className="crm-brand">
        <div className="crm-brand-icon">
          <PhoneCall size={18} />
        </div>
        <div>
          <div className="crm-brand-title">Candidate Voice CRM</div>
          <div className="crm-brand-subtitle">AI Phone Interviewing & Rubric Scoring</div>
        </div>
      </div>

      <div className="crm-status-strip">
        <div className="status-indicator">
          <span className={`status-dot ${isReady ? 'pulse' : ''}`} style={{ background: isReady ? '#10b981' : '#f59e0b' }}></span>
          <span>{isReady ? 'Telephony Online' : 'Provider Warning'}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
          <ShieldCheck size={14} color="#64748b" />
          <span>TCPA Hours Protected</span>
        </div>

        <button
          className="btn btn-secondary btn-sm"
          onClick={onRefresh}
          disabled={loading}
          title="Refresh CRM data"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
        >
          <RefreshCw size={13} className={loading ? 'spin-icon' : ''} />
          <span>{loading ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>
    </header>
  );
}
