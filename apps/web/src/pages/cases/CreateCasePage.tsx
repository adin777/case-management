import { FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Card, CardContent, Chip, CircularProgress, Container, FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../api/client';
import { DynamicField } from '../../components/DynamicField';
import type { Case, Environment, Form, Priority, RequestType, User } from '../../types';

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
  const { data: environments = [] } = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments') });
  const { data: requestTypes = [] } = useQuery({ queryKey: ['request-types', environmentId], queryFn: () => api<RequestType[]>(`/request-types?environment_id=${environmentId}`), enabled: !!environmentId });
  const { data: priorities = [] } = useQuery({ queryKey: ['priorities', environmentId], queryFn: () => api<Priority[]>(`/environments/${environmentId}/priorities`), enabled: !!environmentId });
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api<User[]>('/users') });
  const selectedType = requestTypes.find((item) => item.id === requestTypeId);
  const selectedPriority = priorities.find((item) => item.id === priorityId);
  const { data: form } = useQuery({ queryKey: ['form', selectedType?.form_version_id], queryFn: () => api<Form>(`/forms/${selectedType!.form_version_id}`), enabled: !!selectedType?.form_version_id });
  const { data: caseConfig, error: configError } = useQuery({ queryKey: ['case-config', requestTypeId], queryFn: () => api<{ initial_status_id: string; can_choose_status: boolean; default_priority_id?: string; default_sub_priority_id?: string; statuses: { id: string; label_he: string; is_initial: boolean }[] }>(`/request-types/${requestTypeId}/case-config`), enabled: !!requestTypeId, retry: false });
  useEffect(() => { if (caseConfig) { setWorkflowStatusId(caseConfig.initial_status_id); setPriorityId(caseConfig.default_priority_id || ''); setSubPriorityId(caseConfig.default_sub_priority_id || ''); } }, [caseConfig]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    const missing = form?.fields.filter((field) => field.is_required && (values[field.id!] === undefined || values[field.id!] === ''));
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
      <FormControl required><InputLabel>סביבה</InputLabel><Select label="סביבה" value={environmentId} onChange={(event) => { setEnvironmentId(event.target.value); setRequestTypeId(''); setPriorityId(''); setSubPriorityId(''); }}>{environments.map((environment) => <MenuItem key={environment.id} value={environment.id}>{environment.name_he}</MenuItem>)}</Select></FormControl>
      <FormControl required disabled={!environmentId}><InputLabel>סוג קריאה</InputLabel><Select label="סוג קריאה" value={requestTypeId} onChange={(event) => setRequestTypeId(event.target.value)}>{requestTypes.map((type) => <MenuItem key={type.id} value={type.id}>{type.name_he}</MenuItem>)}</Select></FormControl>
      <TextField label="נושא" required value={title} onChange={(event) => setTitle(event.target.value)} />
      <TextField label="פירוט" required multiline minRows={4} value={description} onChange={(event) => setDescription(event.target.value)} />
      {configError && <Alert severity="error">לא הוגדר סטטוס התחלתי לסוג קריאה זה. יש לפנות למנהל הסביבה.</Alert>}
      <FormControl required disabled={!caseConfig || !caseConfig.can_choose_status}><InputLabel>סטטוס</InputLabel><Select label="סטטוס" value={workflowStatusId} onChange={(event) => setWorkflowStatusId(event.target.value)}>{caseConfig?.statuses.map((status) => <MenuItem key={status.id} value={status.id}>{status.label_he}</MenuItem>)}</Select></FormControl>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <FormControl required fullWidth disabled={!environmentId}><InputLabel>עדיפות</InputLabel><Select label="עדיפות" value={priorityId} onChange={(event) => { setPriorityId(event.target.value); setSubPriorityId(''); }}>{priorities.filter((priority) => priority.is_active).map((priority) => <MenuItem key={priority.id} value={priority.id}>{priority.label_he}</MenuItem>)}</Select></FormControl>
        <FormControl fullWidth disabled={!selectedPriority?.sub_priorities.length}><InputLabel>תת-עדיפות</InputLabel><Select label="תת-עדיפות" value={subPriorityId} onChange={(event) => setSubPriorityId(event.target.value)}>{selectedPriority?.sub_priorities.filter((item) => item.is_active).map((item) => <MenuItem key={item.id} value={item.id}>{item.label_he}</MenuItem>)}</Select></FormControl>
      </Stack>
      <FormControl><InputLabel>משתתפים</InputLabel><Select multiple label="משתתפים" value={participantIds} onChange={(event) => setParticipantIds(typeof event.target.value === 'string' ? event.target.value.split(',') : event.target.value)} renderValue={(selected) => <Stack direction="row" gap={.5} flexWrap="wrap">{selected.map((id) => <Chip key={id} size="small" label={users.find((user) => user.id === id)?.display_name || id} />)}</Stack>}>{users.filter((user) => user.is_active !== false).map((user) => <MenuItem key={user.id} value={user.id}>{user.display_name} · {user.email}</MenuItem>)}</Select></FormControl>
      {form?.fields.map((field) => <DynamicField key={field.id} field={field} value={values[field.id!]} users={users} onChange={(value) => setValues({ ...values, [field.id!]: value })} />)}
      <Button type="submit" variant="contained" size="large" disabled={!form || !caseConfig || submitting}>{submitting ? <><CircularProgress size={20} color="inherit" sx={{ ml: 1 }} />שומר קריאה...</> : 'פתיחת הקריאה'}</Button>
    </Stack></CardContent></Card>
  </Stack></Container>;
}
