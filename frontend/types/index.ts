export type Decision = {
  id: number;
  action_type: string;
  target_supplier_name: string;
  target_product: string;
  justification: string;
  magnitude: string;
  estimated_resolution_days: number;
  confidence_score: number;
  status: 'pending' | 'approved' | 'rejected';
  rejection_reason: string | null;
  created_at: string;
  // full pipeline state fields
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  structured_event: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  affected_regions: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  risk_assessment: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  supplier_impact: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  decision_proposal: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  supervisor_feedback: Record<string, any>;
  iteration_count: number;
  hitl_framing: 'high_confidence' | 'low_confidence';
};
