import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Alert, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
  MenuItem, Stack, Step, StepLabel, Stepper, TextField, Typography,
} from '@mui/material';
import { api } from '../../../api/client';
import type { Environment } from '../../../types';

type Preview = {
  target_environment_name: string;
  request_types: { id: string; name_he: string; requires_approval: boolean }[];
  removed_participant_ids: string[];
  assignee_will_be_removed: boolean;
  global_fields_preserved: number;
  environment_fields_removed: number;
  warning: string;
};
export type TransferRequirements = {
  initial_status_label: string;
  required_fields: { id: string; label: string; field_type: string }[];
  removed_fields: { id: string; label: string }[];
  field_mappings: { label: string }[];
  priorities: { id: string; label_he: string }[];
  sub_priorities: { id: string; priority_id?: string; label_he: string }[];
  assignees: { id: string; display_name: string; email: string }[];
};

const list = <T,>(value: unknown): T[] => Array.isArray(value) ? value as T[] : [];
export function normalizeTransferRequirements(value: unknown): TransferRequirements {
  const raw = value && typeof value === 'object' ? value as Partial<TransferRequirements> : {};
  return {
    initial_status_label: typeof raw.initial_status_label === 'string' ? raw.initial_status_label : '',
    required_fields: list(raw.required_fields),
    removed_fields: list(raw.removed_fields),
    field_mappings: list(raw.field_mappings),
    priorities: list(raw.priorities),
    sub_priorities: list(raw.sub_priorities),
    assignees: list(raw.assignees),
  };
}

type Props = { caseId: string; currentEnvironmentId: string; open: boolean; onClose: () => void; onTransferred: () => void };

export function CaseTransferWizard({ caseId, currentEnvironmentId, open, onClose, onTransferred }: Props) {
  const [step, setStep] = useState(0);
  const [target, setTarget] = useState('');
  const [requestType, setRequestType] = useState('');
  const [assignee, setAssignee] = useState('');
  const [values, setValues] = useState<Record<string, string>>({});
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<Preview>();
  const [requirements, setRequirements] = useState<TransferRequirements>();
  const environmentsQuery = useQuery({ queryKey: ['environments'], queryFn: () => api<Environment[]>('/environments'), enabled: open });
  const environments = Array.isArray(environmentsQuery.data) ? environmentsQuery.data : [];

  const clearDependent = () => {
    setRequestType(''); setAssignee(''); setValues({});
    setPreview(undefined); setRequirements(undefined);
  };
  useEffect(() => {
    if (!open) { setStep(0); setTarget(''); clearDependent(); setError(''); setReason(''); }
  }, [open]);

  async function next() {
    setLoading(true); setError('');
    try {
      if (step === 0) {
        const result = await api<Preview>(`/cases/${caseId}/transfer-preview?target_environment_id=${target}`);
        setPreview({ ...result, request_types: list(result?.request_types), removed_participant_ids: list(result?.removed_participant_ids) });
        setStep(1);
      } else if (step === 1) {
        if (!requestType) throw new Error('יש לבחור סוג קריאה');
        const result = await api<unknown>(`/cases/${caseId}/transfer-requirements?request_type_id=${requestType}`);
        setRequirements(normalizeTransferRequirements(result));
        setStep(2);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'טעינת נתוני ההעברה נכשלה');
    } finally { setLoading(false); }
  }

  async function execute() {
    setLoading(true); setError('');
    try {
      await api(`/cases/${caseId}/transfer`, { method: 'POST', body: JSON.stringify({
        target_environment_id: target, target_request_type_id: requestType, priority_id: null,
        sub_priority_id: null, assignee_id: assignee || null,
        new_field_values: Object.entries(values).map(([field_definition_id, value]) => ({ field_definition_id, value })),
        reason: reason || null,
      }) });
      onTransferred(); onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'העברת הקריאה נכשלה');
    } finally { setLoading(false); }
  }

  const req = requirements ?? normalizeTransferRequirements(undefined);
  return <Dialog open={open} onClose={loading ? undefined : onClose} fullWidth maxWidth="md">
    <DialogTitle>העברת קריאה לסביבה אחרת</DialogTitle>
    <DialogContent><Stack spacing={2} sx={{ pt: 1 }}>
      <Stepper activeStep={step}>{['סביבת יעד', 'השוואה', 'אישור'].map(label => <Step key={label}><StepLabel>{label}</StepLabel></Step>)}</Stepper>
      {(error || environmentsQuery.error) && <Alert severity="error">{error || (environmentsQuery.error as Error).message}</Alert>}
      {loading && <Stack direction="row" spacing={1} alignItems="center"><CircularProgress size={20}/><Typography>טוען נתונים…</Typography></Stack>}
      {step === 0 && <TextField select label="סביבת יעד" value={target} disabled={loading} onChange={event => { setTarget(event.target.value); clearDependent(); }}>
        {environments.filter(environment => environment.is_active && environment.id !== currentEnvironmentId).map(environment => <MenuItem key={environment.id} value={environment.id}>{environment.name_he}</MenuItem>)}
      </TextField>}
      {step === 1 && preview && <>
        {preview.warning && <Alert severity="warning">{preview.warning}</Alert>}
        <Typography>העברה אל: <strong>{preview.target_environment_name}</strong></Typography>
        <Typography>שדות גלובליים שיישמרו: {preview.global_fields_preserved}</Typography>
        <Typography>שדות סביבתיים שיוסרו: {preview.environment_fields_removed}</Typography>
        <Typography>משתתפים שיוסרו: {preview.removed_participant_ids.length}</Typography>
        <Typography>מטפל: {preview.assignee_will_be_removed ? 'יוסר כי אינו זכאי בסביבת היעד' : 'יישמר אם הוא זכאי'}</Typography>
        <TextField select label="סוג קריאה בסביבת היעד" value={requestType} disabled={loading} onChange={event => setRequestType(event.target.value)}>
          {preview.request_types.map(type => <MenuItem key={type.id} value={type.id}>{type.name_he}</MenuItem>)}
        </TextField>
      </>}
      {step === 2 && preview && requirements && <>
        <Alert severity="info">הסטטוס, העדיפות ותת־העדיפות הגלובליים יישמרו ללא שינוי.</Alert>
        <TextField select label="מטפל בסביבת היעד" value={assignee} disabled={loading} onChange={event => setAssignee(event.target.value)}>
          <MenuItem value="">ללא שיוך</MenuItem>{req.assignees.map(user => <MenuItem key={user.id} value={user.id}>{user.display_name} · {user.email}</MenuItem>)}
        </TextField>
        <Alert severity="warning">העברת הקריאה תשנה את סביבת העבודה. המידע ההיסטורי יישמר.</Alert>
        <Typography>סביבה: {preview.target_environment_name}</Typography>
        <TextField label="סיבת ההעברה (רשות)" multiline value={reason} onChange={event => setReason(event.target.value)}/>
      </>}
    </Stack></DialogContent>
    <DialogActions><Button disabled={loading} onClick={onClose}>ביטול</Button>{step > 0 && <Button disabled={loading} onClick={() => setStep(current => current - 1)}>חזרה</Button>}{step < 2 ? <Button variant="contained" disabled={loading || (step === 0 && !target)} onClick={next}>המשך</Button> : <Button variant="contained" color="warning" disabled={loading} onClick={execute}>העברת הקריאה</Button>}</DialogActions>
  </Dialog>;
}
