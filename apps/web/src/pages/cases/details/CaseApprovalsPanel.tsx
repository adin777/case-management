import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Card, CardContent, Chip, Collapse, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../../api/client';

type Task = { id:string; step_order:number; step_name:string; approver_type:string; approver_name?:string; status:string; comment?:string; requested_at:string; decided_at?:string; can_decide:boolean };
type Attempt = { id:string; attempt_number:number; status:string; tasks:Task[] };
type ApprovalPayload = { current_approval:Attempt|null; approval_history:Attempt[]; can_resubmit:boolean };
const statusLabel:Record<string,string> = { pending:'ממתין', approved:'אושר', rejected:'נדחה', returned:'הוחזר לתיקון', cancelled:'בוטל' };

function AttemptView({ attempt, current, onDecision }:{attempt:Attempt;current?:boolean;onDecision?:(task:Task)=>void}) {
  return <Stack spacing={2}>{attempt.tasks.map(task => <Stack key={task.id} gap={.5}>
    <Stack direction={{xs:'column',md:'row'}} gap={1} alignItems={{md:'center'}}>
      <Typography fontWeight={800}>שלב {task.step_order}: {task.step_name}</Typography>
      <Typography sx={{flex:1}}>{task.approver_name || 'מאשר'} · {task.approver_type}</Typography>
      <Chip label={statusLabel[task.status] || task.status} color={task.status === 'rejected' ? 'error' : task.status === 'approved' ? 'success' : 'default'}/>
      {current && task.can_decide && <Button variant="contained" onClick={() => onDecision?.(task)}>החלטה</Button>}
    </Stack>
    <Typography variant="caption">נשלח: {new Date(task.requested_at).toLocaleString('he-IL')}{task.decided_at ? ` · הוחלט: ${new Date(task.decided_at).toLocaleString('he-IL')}` : ''}</Typography>
    {task.comment && <Alert severity={task.status === 'rejected' ? 'error' : 'info'}>סיבה/הערה: {task.comment}</Alert>}
  </Stack>)}</Stack>;
}

export function CaseApprovalsPanel({caseId}:{caseId:string}) {
  const qc=useQueryClient(); const [selected,setSelected]=useState<Task>(); const [comment,setComment]=useState(''); const [error,setError]=useState(''); const [historyOpen,setHistoryOpen]=useState(false);
  const {data}=useQuery({queryKey:['case-approvals',caseId],queryFn:()=>api<ApprovalPayload>(`/cases/${caseId}/approvals`)});
  const refresh=()=>Promise.all([qc.invalidateQueries({queryKey:['case-approvals',caseId]}),qc.invalidateQueries({queryKey:['case',caseId]}),qc.invalidateQueries({queryKey:['pending-approvals']})]);
  const decision=useMutation({mutationFn:(value:'approved'|'rejected')=>api(`/approval-tasks/${selected!.id}/decision`,{method:'POST',body:JSON.stringify({decision:value,comment:comment.trim()||null})}),onSuccess:async()=>{setSelected(undefined);setComment('');await refresh()},onError:e=>setError((e as Error).message)});
  const resubmit=useMutation({mutationFn:()=>api(`/cases/${caseId}/approvals/resubmit`,{method:'POST'}),onSuccess:refresh,onError:e=>setError((e as Error).message)});
  const current=data?.current_approval;
  return <Card><CardContent><Typography variant="h6">אישורים</Typography><Divider sx={{my:2}}/>{error&&<Alert severity="error">{error}</Alert>}
    {!current ? <Typography color="text.secondary">לא נדרש תהליך אישור</Typography> : <Stack spacing={2}>
      <Stack direction="row" justifyContent="space-between" alignItems="center"><Typography fontWeight={800}>ניסיון אישור {current.attempt_number}</Typography><Chip label={statusLabel[current.status] || current.status}/></Stack>
      <AttemptView attempt={current} current onDecision={setSelected}/>
      {data?.can_resubmit && <Button variant="contained" onClick={()=>resubmit.mutate()} disabled={resubmit.isPending}>שליחה מחדש לאישור</Button>}
      {!!data?.approval_history.length && <><Button variant="text" onClick={()=>setHistoryOpen(value=>!value)}>{historyOpen?'הסתרת היסטוריית אישורים':'הצגת היסטוריית אישורים'}</Button><Collapse in={historyOpen}><Stack spacing={3}>{data.approval_history.map(attempt=><Stack key={attempt.id} spacing={1}><Typography fontWeight={800}>ניסיון {attempt.attempt_number} · {statusLabel[attempt.status] || attempt.status}</Typography><AttemptView attempt={attempt}/></Stack>)}</Stack></Collapse></>}
    </Stack>}
    <Dialog open={!!selected} onClose={()=>setSelected(undefined)} fullWidth><DialogTitle>החלטה בשלב {selected?.step_order}</DialogTitle><DialogContent><TextField sx={{mt:1}} fullWidth multiline label="הערה (חובה בדחייה)" value={comment} onChange={e=>setComment(e.target.value)}/></DialogContent><DialogActions><Button onClick={()=>setSelected(undefined)}>ביטול</Button><Button color="error" disabled={!comment.trim()||decision.isPending} onClick={()=>decision.mutate('rejected')}>דחייה</Button><Button variant="contained" disabled={decision.isPending} onClick={()=>decision.mutate('approved')}>אישור</Button></DialogActions></Dialog>
  </CardContent></Card>;
}
