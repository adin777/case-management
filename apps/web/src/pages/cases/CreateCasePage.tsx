import { FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Card, CardContent, Chip, CircularProgress, Container, FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../api/client';
import { DynamicField } from '../../components/DynamicField';
import type { Case, Environment, Form, RequestType, User } from '../../types';
import { activeRequestTypes, caseCreationConfigurationUrl } from './caseCreationSources';

type CreationType=RequestType&{initial_status_id:string;can_choose_status:boolean;statuses:{id:string;label_he:string;is_initial:boolean}[];form?:Form;default_priority_id?:string;default_sub_priority_id?:string};
type CreationConfig={request_types:CreationType[];priorities:{id:string;label_he:string;is_active:boolean}[];sub_priorities:{id:string;priority_id?:string;label_he:string;is_active:boolean}[];participants:User[]};

export function CreateCasePage() {
  const navigate = useNavigate();
  const [environmentId, setEnvironmentId] = useState('');
  const [requestTypeId, setRequestTypeId] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priorityId, setPriorityId] = useState('');
  const [subPriorityId, setSubPriorityId] = useState('');
  const [workflowStatusId, setWorkflowStatusId] = useState('');
  const [participantIds, setParticipantIds] = useState<string[]>([]);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { data: environments = [] } = useQuery({ queryKey: ['case-creation-environments'], queryFn: () => api<Environment[]>('/case-creation/environments') });
  const { data: creationConfig, error: configError } = useQuery({ queryKey: ['case-creation-configuration', environmentId], queryFn: () => api<CreationConfig>(caseCreationConfigurationUrl(environmentId)), enabled: !!environmentId, retry:false });
  const requestTypeRows=creationConfig?.request_types||[];const priorities=creationConfig?.priorities||[];const subPriorities=creationConfig?.sub_priorities||[];const users=creationConfig?.participants||[];
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') });
  const requestTypes = activeRequestTypes(requestTypeRows, environmentId);
  const selectedType = requestTypes.find((item) => item.id === requestTypeId);
  const caseConfig=selectedType as CreationType|undefined;const form=caseConfig?.form;
  useEffect(() => { if (caseConfig) { setWorkflowStatusId(caseConfig.initial_status_id); setPriorityId(caseConfig.default_priority_id || ''); setSubPriorityId(caseConfig.default_sub_priority_id || ''); } }, [caseConfig]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    const missing = form?.fields.filter((field) => field.is_active !== false && field.is_required && (values[field.id!] === undefined || values[field.id!] === ''));
    if (missing?.length) { setError(`יש למלא: ${missing.map((field) => field.label_he).join(', ')}`); return; }
    if (!environmentId || !requestTypeId || !title.trim() || !description.trim() || !workflowStatusId || !priorityId) { setError('יש למלא את כל שדות הליבה'); return; }
    setSubmitting(true);
    try {
      const result = await api<Case>('/cases', { method: 'POST', body: JSON.stringify({
        environment_id: environmentId, request_type_id: requestTypeId, title, description,
        workflow_status_id: workflowStatusId, priority_id: priorityId,
        sub_priority_id: subPriorityId || null, participant_ids: participantIds,
        values: Object.entries(values).map(([field_definition_id, value]) => ({ field_definition_id, value })),
      }) });
      navigate(`/cases/${result.id}`);
    } catch (caught) { setError((caught as Error).message); }
    finally { setSubmitting(false); }
  }

  return <Container maxWidth="md"><Stack spacing={3}>
    <div><Typography variant="h4" fontWeight={800}>פתיחת קריאה חדשה</Typography><Typography color="text.secondary">מלאו את פרטי הליבה והוסיפו משתתפים לפי הצורך</Typography></div>
    {error && <Alert severity="error">{error}</Alert>}
    <Card variant="outlined"><CardContent><Stack component="form" onSubmit={submit} spacing={2.5}>
      <FormControl required><InputLabel>סביבה</InputLabel><Select label="סביבה" value={environmentId} onChange={(event) => { setEnvironmentId(event.target.value); setRequestTypeId(''); setPriorityId(''); setSubPriorityId(''); setWorkflowStatusId(''); setValues({}); }}>{environments.map((environment) => <MenuItem key={environment.id} value={environment.id}>{environment.name_he}</MenuItem>)}</Select></FormControl>
      <TextField label="נושא" required value={title} onChange={(event) => setTitle(event.target.value)} />
      <TextField label="תיאור" required multiline minRows={4} value={description} onChange={(event) => setDescription(event.target.value)} />
      <FormControl required disabled={!environmentId}><InputLabel>סוג קריאה</InputLabel><Select label="סוג קריאה" value={requestTypeId} onChange={(event) => setRequestTypeId(event.target.value)}>{requestTypes.map((type) => <MenuItem key={type.id} value={type.id}>{type.name_he}</MenuItem>)}</Select></FormControl>
      {configError && <Alert severity="error" action={me?.is_system_admin ? <Button color="inherit" href="/admin/environments">מעבר להגדרות סטטוס</Button> : undefined}>{me?.is_system_admin ? `לא ניתן לפתוח קריאה מסוג "${selectedType?.name_he || ''}". לא הוגדר סטטוס התחלתי בתהליך העבודה המשויך לסוג קריאה זה.` : 'לא ניתן לפתוח כרגע קריאה מסוג זה. יש לפנות למנהל הסביבה.'}</Alert>}
      {caseConfig?.can_choose_status ? <FormControl required><InputLabel>סטטוס</InputLabel><Select label="סטטוס" value={workflowStatusId} onChange={(event) => setWorkflowStatusId(event.target.value)}>{caseConfig.statuses.map((status) => <MenuItem key={status.id} value={status.id}>{status.label_he}</MenuItem>)}</Select></FormControl> : caseConfig && <TextField label="סטטוס" value={caseConfig.statuses.find((status) => status.id === workflowStatusId)?.label_he || ''} slotProps={{ input: { readOnly: true } }} />}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <FormControl required fullWidth disabled={!environmentId}><InputLabel>עדיפות</InputLabel><Select label="עדיפות" value={priorityId} onChange={(event) => { setPriorityId(event.target.value); setSubPriorityId(''); }}>{priorities.map((priority) => <MenuItem key={priority.id} value={priority.id}>{priority.label_he}</MenuItem>)}</Select></FormControl>
        <FormControl fullWidth disabled={!subPriorities.some(row=>!row.priority_id||row.priority_id===priorityId)}><InputLabel>תת-עדיפות</InputLabel><Select label="תת-עדיפות" value={subPriorityId} onChange={(event) => setSubPriorityId(event.target.value)}>{subPriorities.filter(row=>!row.priority_id||row.priority_id===priorityId).map((item) => <MenuItem key={item.id} value={item.id}>{item.label_he}</MenuItem>)}</Select></FormControl>
      </Stack>
      <FormControl><InputLabel>משתתפים</InputLabel><Select multiple label="משתתפים" value={participantIds} onChange={(event) => setParticipantIds(typeof event.target.value === 'string' ? event.target.value.split(',') : event.target.value)} renderValue={(selected) => <Stack direction="row" gap={.5} flexWrap="wrap">{selected.map((id) => <Chip key={id} size="small" label={users.find((user) => user.id === id)?.display_name || id} />)}</Stack>}>{users.filter((user) => user.is_active !== false).map((user) => <MenuItem key={user.id} value={user.id}>{user.display_name} · {user.email}</MenuItem>)}</Select></FormControl>
      {form?.fields.filter((field) => field.is_active !== false).map((field) => <DynamicField key={field.id} field={field} value={values[field.id!]} users={users} onChange={(value) => setValues({ ...values, [field.id!]: value })} />)}
      <Button type="submit" variant="contained" size="large" disabled={!caseConfig || submitting || !environmentId || !requestTypeId || !title.trim() || !description.trim() || !workflowStatusId || !priorityId}>{submitting ? <><CircularProgress size={20} color="inherit" sx={{ ml: 1 }} />שומר קריאה...</> : 'פתיחת הקריאה'}</Button>
    </Stack></CardContent></Card>
  </Stack></Container>;
}
