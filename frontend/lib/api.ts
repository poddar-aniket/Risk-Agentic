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

export const getSuppliers = async () => {
  try {
    const res = await fetch('/api/suppliers', { cache: 'no-store' });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching suppliers:', error);
    return [];
  }
};

export const addSupplier = (payload: any) => fetch('/api/suppliers', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

export const updateSupplier = (id: number, payload: any) => fetch(`/api/suppliers/${id}`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

export const deleteSupplier = (id: number) => fetch(`/api/suppliers/${id}`, {
  method: 'DELETE',
});

export const getInventory = async () => {
  try {
    const res = await fetch('/api/inventory', { cache: 'no-store' });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    console.error('Error fetching inventory:', error);
    return [];
  }
};

export const addInventory = (payload: any) => fetch('/api/inventory', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

export const updateInventory = (id: number, payload: any) => fetch(`/api/inventory/${id}`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

export const deleteInventory = (id: number) => fetch(`/api/inventory/${id}`, {
  method: 'DELETE',
});
