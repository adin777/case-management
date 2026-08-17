import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Box, Button, Checkbox, Container, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, Paper, Stack, Tab, Tabs, TextField } from '@mui/material';
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

const labels = ['כללי', 'הגדרות קריאה', 'שדות הסביבה', 'משתמשים והרשאות סביבה', 'שיוך אוטומטי', 'אוטומציות', 'אישורים', 'SLA', 'ניהול ידע'];
const empty = { name_he: '', name_en: '', description: '' };

export function EnvironmentsPage() {
  const client = useQueryClient(); const [selected, setSelected] = useState<Environment>();
  const [activeOnly, setActiveOnly] = useState(true); const [tab, setTab] = useState(0);
  const [open, setOpen] = useState(false); const [cloneOpen, setCloneOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [cloneForm, setCloneForm] = useState({ ...empty, copy_memberships: false, copy_knowledge: false });
  const { data: items = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  async function refresh(item: Environment) { setSelected(item); await client.invalidateQueries({ queryKey: ['environments'] }); }
  async function create() { const item = await api<Environment>('/environments', { method: 'POST', body: JSON.stringify(form) }); setOpen(false); setForm(empty); await refresh(item); }
  async function clone() { if (!selected) return; const result = await api<{environment: Environment}>(`/environments/${selected.id}/clone`, { method: 'POST', body: JSON.stringify(cloneForm) }); setCloneOpen(false); await refresh(result.environment); }
  async function setArchived(archive:boolean) { if(!selected)return; const item=await api<Environment>(`/environments/${selected.id}/${archive?'archive':'restore'}`,{method:'POST'}); await refresh(item); }
  return <Container maxWidth="xl"><Stack spacing={3}>
    <EnvironmentList environments={filterEnvironments(items, activeOnly)} selected={selected} activeOnly={activeOnly} onActiveOnlyChange={setActiveOnly} onSelect={(item) => { setSelected(item); setTab(0); }} onCreate={() => setOpen(true)}/>
    {selected && <Paper variant="outlined"><Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable" scrollButtons="auto">{labels.map((label) => <Tab key={label} label={label}/>)}</Tabs><Box sx={{ p: { xs: 2, md: 3 } }}><Stack spacing={2}>
      <Box sx={{display:'flex',gap:1}}><Button variant="outlined" onClick={() => { setCloneForm({ ...empty, name_he: `${selected.name_he} - עותק`, name_en: `${selected.name_en} copy`, copy_memberships: false, copy_knowledge: false }); setCloneOpen(true); }}>שכפול סביבה</Button><Button color={selected.is_active?'warning':'success'} onClick={()=>setArchived(selected.is_active)}>{selected.is_active?'העברה לארכיון':'שחזור סביבה'}</Button></Box>
      {tab === 0 && <EnvironmentGeneralTab environment={selected} onSaved={() => client.invalidateQueries({ queryKey: ['environments'] })}/>} {tab === 1 && <SystemFieldsTab environment={selected}/>} {tab === 2 && <CaseFieldsTab environment={selected}/>} {tab === 3 && <EnvironmentAccessTab environment={selected}/>} {tab === 4 && <EnvironmentAssignmentRulesTab environment={selected}/>} {tab === 5 && <AutomationRulesTab environment={selected}/>} {tab === 6 && <ApprovalFlowsTab environment={selected}/>} {tab === 7 && <SlaPoliciesTab environment={selected}/>} {tab === 8 && <KnowledgeTab environment={selected}/>} </Stack></Box></Paper>}
  </Stack>
  <Dialog open={open} onClose={() => setOpen(false)} fullWidth><DialogTitle>סביבה חדשה</DialogTitle><DialogContent><Stack spacing={2} sx={{ mt: 1 }}>{(['name_he', 'name_en', 'description'] as const).map((key) => <TextField key={key} label={{ name_he: 'שם בעברית', name_en: 'שם באנגלית', description: 'תיאור' }[key]} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })}/>)}</Stack></DialogContent><DialogActions><Button onClick={() => setOpen(false)}>ביטול</Button><Button variant="contained" disabled={!form.name_he.trim() || !form.name_en.trim()} onClick={create}>יצירה</Button></DialogActions></Dialog>
  <Dialog open={cloneOpen} onClose={() => setCloneOpen(false)} fullWidth><DialogTitle>שכפול סביבה</DialogTitle><DialogContent><Stack spacing={2} sx={{ mt: 1 }}><Alert severity="info">יועתקו סוגי קריאות, סטטוסים, עדיפויות, שדות, טפסים, אוטומציות, אישורים ו־SLA. קריאות, תגובות, קבצים, Audit והיסטוריה לא יועתקו.</Alert><TextField label="שם בעברית" value={cloneForm.name_he} onChange={e=>setCloneForm({...cloneForm,name_he:e.target.value})}/><TextField label="שם באנגלית" value={cloneForm.name_en} onChange={e=>setCloneForm({...cloneForm,name_en:e.target.value})}/><TextField label="תיאור" value={cloneForm.description} onChange={e=>setCloneForm({...cloneForm,description:e.target.value})}/><FormControlLabel control={<Checkbox checked={cloneForm.copy_memberships} onChange={e=>setCloneForm({...cloneForm,copy_memberships:e.target.checked})}/>} label="העתק שיוכי משתמשים וקבוצות"/><FormControlLabel control={<Checkbox checked={cloneForm.copy_knowledge} onChange={e=>setCloneForm({...cloneForm,copy_knowledge:e.target.checked})}/>} label="העתק מאגר ידע"/></Stack></DialogContent><DialogActions><Button onClick={() => setCloneOpen(false)}>ביטול</Button><Button variant="contained" disabled={!cloneForm.name_he.trim() || !cloneForm.name_en.trim()} onClick={clone}>שכפול</Button></DialogActions></Dialog>
  </Container>;
}
