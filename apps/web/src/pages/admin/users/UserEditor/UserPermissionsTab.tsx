import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Accordion, AccordionDetails, AccordionSummary, Alert, Button, MenuItem, Paper, Stack, TextField, Typography } from '@mui/material';
import { ExpandMore } from '@mui/icons-material';
import { api } from '../../../../api/client';
import type { Environment, User } from '../../../../types';
import { PermissionLevelControl, type UserAccessLevel } from './PermissionLevelControl';
import type { PermissionDomain } from './types';

export function UserPermissionsTab({ user, environments }: { user: User; environments: Environment[] }) {
  const client = useQueryClient(); const [environmentId, setEnvironmentId] = useState('');
  const [levels, setLevels] = useState<Record<string, UserAccessLevel>>({}); const [message, setMessage] = useState('');
  const { data: domains = [] } = useQuery({ queryKey: ['access-domains'], queryFn: () => api<PermissionDomain[]>('/access/domains') });
  const { data: overrides = {} } = useQuery({ queryKey: ['user-overrides', user.id, environmentId], queryFn: () => api<Record<string, UserAccessLevel>>(`/access/users/${user.id}/overrides${environmentId ? `?environment_id=${environmentId}` : ''}`) });
  useEffect(() => { setLevels(Object.fromEntries(domains.map((domain) => [domain.code, overrides[domain.code] || 'inherit']))); }, [domains, overrides]);
  const visible = domains.filter((domain) => environmentId ? domain.scope !== 'global' : domain.scope !== 'environment');
  const categories = useMemo(() => [...new Set(visible.map((domain) => domain.category))], [visible]);
  async function save() { const payload = Object.fromEntries(visible.map((domain) => [domain.code, levels[domain.code] || 'inherit'])); await api('/access/bulk', { method: 'POST', body: JSON.stringify({ subject_type: 'users', subject_ids: [user.id], environment_id: environmentId || null, levels: payload }) }); setMessage('חריגות ההרשאה נשמרו'); await client.invalidateQueries({ queryKey: ['user-overrides', user.id] }); await client.invalidateQueries({ queryKey: ['effective-access', user.id] }); }
  return <Stack spacing={2}>{message && <Alert severity="success">{message}</Alert>}<TextField select label="תחולה" value={environmentId} onChange={(event) => setEnvironmentId(event.target.value)}><MenuItem value="">כללי</MenuItem>{environments.map((environment) => <MenuItem key={environment.id} value={environment.id}>{environment.name_he}</MenuItem>)}</TextField>
    {categories.map((category) => <Accordion key={category} defaultExpanded><AccordionSummary expandIcon={<ExpandMore/>}><Typography fontWeight={800}>{category}</Typography></AccordionSummary><AccordionDetails><Stack spacing={2}>{visible.filter((domain) => domain.category === category).map((domain) => <Paper key={domain.code} variant="outlined" sx={{ p: 1.5 }}><Typography fontWeight={700}>{domain.name_he}</Typography><Typography variant="body2" color="text.secondary" mb={1}>{domain.description_he}</Typography><PermissionLevelControl inherit value={levels[domain.code] || 'inherit'} onChange={(level) => setLevels({ ...levels, [domain.code]: level })}/></Paper>)}</Stack></AccordionDetails></Accordion>)}
    <Button variant="contained" sx={{ position: 'sticky', bottom: 8, alignSelf: 'flex-end' }} onClick={save}>שמירת הרשאות</Button></Stack>;
}
