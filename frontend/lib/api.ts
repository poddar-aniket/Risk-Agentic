export const getQueue = async () => {
  try {
    const res = await fetch('/api/queue', { cache: 'no-store' });
    if (!res.ok) {
      console.error('Failed to fetch queue', res.statusText);
      return [];
    }
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching queue:', error);
    return [];
  }
};
export const approveDecision = (id: number) => fetch(`/api/queue/${id}/approve`, { method: 'POST' })
export const rejectDecision = (id: number, reason: string) => fetch(`/api/queue/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }), headers: { 'Content-Type': 'application/json' } })
export const triggerPipeline = () => fetch('/api/pipeline/run', { method: 'POST' })
