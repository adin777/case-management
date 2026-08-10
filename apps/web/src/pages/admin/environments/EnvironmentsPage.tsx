import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Box, Button, Container, Dialog, DialogActions, DialogContent, DialogTitle, Paper, Stack, Tab, Tabs, TextField } from '@mui/material';
import { api } from '../../../api/client';
import type { Environment } from '../../../types';
import { EnvironmentList } from './EnvironmentList';
import { EnvironmentGeneralTab } from './tabs/EnvironmentGeneralTab';
import { CaseFieldsTab } from './tabs/CaseFieldsTab';
import { EnvironmentAccessTab } from './tabs/EnvironmentAccessTab';
import { EnvironmentAssignmentRulesTab } from './tabs/EnvironmentAssignmentRulesTab';
import { AutomationRulesTab } from './tabs/AutomationRulesTab';
import { ApprovalFlowsTab } from './tabs/ApprovalFlowsTab';
import { SlaPoliciesTab } from './tabs/SlaPoliciesTab';
import { SystemFieldsTab } from './system-fields/SystemFieldsTab';
import { filterEnvironments } from './environmentFilter';
import { KnowledgeTab } from './tabs/KnowledgeTab';

const labels = ['כללי', 'שדות מערכת', 'שדות נוספים', 'משתמשים', 'שיוך אוטומטי', 'אוטומציות', 'אישורים', 'SLA', 'ניהול ידע'];

export function EnvironmentsPage() {
  const client = useQueryClient(); const [selected, setSelected] = useState<Environment>();
  const [activeOnly, setActiveOnly] = useState(true);
  const [tab, setTab] = useState(0); const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: '', name_he: '', name_en: '', description: '' });
  const { data: items = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  async function create() { const item = await api<Environment>('/environments', { method: 'POST', body: JSON.stringify(form) }); setOpen(false); setSelected(item); client.invalidateQueries({ queryKey: ['environments'] }); }
  return <Container maxWidth="xl"><Stack spacing={3}>
    <EnvironmentList environments={filterEnvironments(items, activeOnly)} selected={selected} activeOnly={activeOnly} onActiveOnlyChange={setActiveOnly} onSelect={(item) => { setSelected(item); setTab(0); }} onCreate={() => setOpen(true)}/>
    {selected && <Paper variant="outlined"><Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable" scrollButtons="auto">{labels.map((label) => <Tab key={label} label={label}/>)}</Tabs><Box sx={{ p: { xs: 2, md: 3 } }}>
      {tab === 0 && <EnvironmentGeneralTab environment={selected} onSaved={() => client.invalidateQueries({ queryKey: ['environments'] })}/>} {tab === 1 && <SystemFieldsTab environment={selected}/>} {tab === 2 && <CaseFieldsTab environment={selected}/>} {tab === 3 && <EnvironmentAccessTab environment={selected}/>} {tab === 4 && <EnvironmentAssignmentRulesTab environment={selected}/>} {tab === 5 && <AutomationRulesTab environment={selected}/>} {tab === 6 && <ApprovalFlowsTab environment={selected}/>} {tab === 7 && <SlaPoliciesTab environment={selected}/>} {tab === 8 && <KnowledgeTab environment={selected}/>} </Box></Paper>}
  </Stack><Dialog open={open} onClose={() => setOpen(false)} fullWidth><DialogTitle>סביבה חדשה</DialogTitle><DialogContent><Stack spacing={2} sx={{ mt: 1 }}>{(['code', 'name_he', 'name_en', 'description'] as const).map((key) => <TextField key={key} label={{ code: 'קוד', name_he: 'שם בעברית', name_en: 'שם באנגלית', description: 'תיאור' }[key]} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })}/>)}</Stack></DialogContent><DialogActions><Button onClick={() => setOpen(false)}>ביטול</Button><Button variant="contained" onClick={create}>יצירה</Button></DialogActions></Dialog></Container>;
}
