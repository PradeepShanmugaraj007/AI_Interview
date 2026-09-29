/**
 * API client wrapper for FastAPI CRM endpoints.
 */

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = 'Request failed';
    try {
      const data = await response.json();
      errorDetail = typeof data.detail === 'string' ? data.detail : (data.message || JSON.stringify(data));
    } catch {
      errorDetail = await response.text();
    }
    throw new Error(errorDetail || `HTTP ${response.status}`);
  }
  return response.json();
}

export const api = {
  async getHealth() {
    return handleResponse(await fetch('/health'));
  },

  async getStats() {
    return handleResponse(await fetch('/api/crm/stats'));
  },

  async getCandidates() {
    return handleResponse(await fetch('/api/crm/candidates'));
  },

  async getCandidate(id) {
    return handleResponse(await fetch(`/api/crm/candidates/${id}`));
  },

  async createCandidate(formData) {
    return handleResponse(await fetch('/api/crm/candidates', {
      method: 'POST',
      body: formData,
    }));
  },

  async triggerCall(candidateId) {
    return handleResponse(await fetch(`/api/crm/candidates/${candidateId}/call`, {
      method: 'POST',
    }));
  },

  async hangupCall(candidateId) {
    return handleResponse(await fetch(`/api/crm/candidates/${candidateId}/hangup`, {
      method: 'POST',
    }));
  },

  async getInterview(interviewId) {
    return handleResponse(await fetch(`/api/crm/interviews/${interviewId}`));
  },
};
