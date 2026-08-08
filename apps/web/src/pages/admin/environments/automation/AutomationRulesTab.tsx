import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Paper, Stack, Typography } from '@mui/material';
import { api } from '../../../../api/client';
import type { AutomationRule, Environment } from '../../../../types';
import { AutomationRuleEditor } from './AutomationRuleEditor';
import type { FieldDiscovery } from './types';

export function AutomationRulesTab({ environment }: { environment: Environment }) {
  const client = useQueryClient(); const [editing, setEditing] = useState<AutomationRule>();
  const { data: rules = [] } = useQuery({ queryKey: ['automation-rules', environment.id], queryFn: () => api<AutomationRule[]>(`/automation-rules?environment_id=${environment.id}`) });
  const { data: fields = { trigger_fields: [], target_fields: [] } } = useQuery({ queryKey: ['automation-fields', environment.id], queryFn: () => api<FieldDiscovery>(`/environments/${environment.id}/automation-fields`) });
  async function save(payload: object) { await api(editing ? `/automation-rules/${editing.id}` : '/automation-rules', { method: editing ? 'PATCH' : 'POST', body: JSON.stringify(payload) }); setEditing(undefined); await client.invalidateQueries({ queryKey: ['automation-rules', environment.id] }); }
  return <Stack spacing={2}>{rules.map((rule) => <Paper key={rule.id} variant="outlined" sx={{ p: 2 }}><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between"><span><Typography fontWeight={800}>{rule.name}</Typography><Typography variant="body2" color="text.secondary">{rule.is_active ? 'פעילה' : 'מושבתת'} · סדר {rule.priority}</Typography></span><Button onClick={() => setEditing(rule)}>עריכה</Button></Stack></Paper>)}<AutomationRuleEditor environment={environment} fields={fields} rule={editing} onSave={save} onCancel={() => setEditing(undefined)}/></Stack>;
}
