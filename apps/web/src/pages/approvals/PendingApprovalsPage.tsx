import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Alert, Button, Card, CardContent, Chip, CircularProgress, Container, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../api/client';

type PendingApproval = { task_id: string; case_id: string; case_number: string; title: string; environment: string; request_type: string; step_name: string; requested_at: string; status: string };

export function PendingApprovalsPage() {
  const qc = useQueryClient(); const [selected, setSelected] = useState<PendingApproval>(); const [comment, setComment] = useState(''); const [error, setError] = useState('');
  const query = useQuery({ queryKey: ['pending-approvals'], queryFn: () => api<PendingApproval[]>('/approvals/pending-for-me') });
  const decision = useMutation({ mutationFn: ({ task, value }: { task: PendingApproval; value: 'approved'|'rejected' }) => api(`/approval-tasks/${task.task_id}/decision`, { method: 'POST', body: JSON.stringify({ decision: value, comment: comment.trim() || null }) }), onSuccess: () => { setSelected(undefined); setComment(''); qc.invalidateQueries({ queryKey: ['pending-approvals'] }); }, onError: (caught) => setError((caught as Error).message) });
  if (query.isLoading) return <Stack alignItems="center" py={8}><CircularProgress/></Stack>;
  return <Container maxWidth="lg"><Stack spacing={2.5}><div><Typography variant="h4">קריאות ממתינות לאישור</Typography><Typography color="text.secondary">משימות אישור פעילות שהוקצו לך</Typography></div>{error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
    {!query.data?.length ? <Card><CardContent sx={{ py: 7, textAlign: 'center' }}><Typography variant="h6">אין כרגע קריאות שממתינות לאישורך</Typography></CardContent></Card> : query.data.map((row) => <Card key={row.task_id}><CardContent><Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}><Stack><Typography component={Link} to={`/cases/${row.case_id}`} variant="h6" color="primary">{row.case_number} · {row.title}</Typography><Typography color="text.secondary">{row.environment} · {row.request_type} · {row.step_name}</Typography><Typography variant="caption">נשלחה: {new Date(row.requested_at).toLocaleString('he-IL')}</Typography></Stack><Stack direction="row" gap={1} alignItems="center"><Chip label="ממתינה" color="warning"/><Button variant="contained" onClick={() => setSelected(row)}>טיפול</Button></Stack></Stack></CardContent></Card>)}
    <Dialog open={!!selected} onClose={() => setSelected(undefined)} fullWidth maxWidth="sm"><DialogTitle>החלטה עבור {selected?.case_number}</DialogTitle><DialogContent><TextField sx={{ mt: 1 }} fullWidth multiline minRows={3} label="הערה (חובה בדחייה)" value={comment} onChange={(event) => setComment(event.target.value)}/></DialogContent><DialogActions><Button onClick={() => setSelected(undefined)}>ביטול</Button><Button color="error" disabled={!comment.trim() || decision.isPending} onClick={() => selected && decision.mutate({ task: selected, value: 'rejected' })}>דחייה</Button><Button variant="contained" disabled={decision.isPending} onClick={() => selected && decision.mutate({ task: selected, value: 'approved' })}>אישור</Button></DialogActions></Dialog>
  </Stack></Container>;
}
