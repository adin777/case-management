import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FactCheckOutlined, History } from '@mui/icons-material';
import { Alert, Box, Button, Chip, Collapse, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from '@mui/material';
import { api } from '../../../api/client';
import { CaseSection } from './CaseSection';

type Task = { id:string; step_order:number; step_name:string; approver_type:string; approver_name?:string; status:string; comment?:string; requested_at:string; decided_at?:string; can_decide:boolean };
type Attempt = { id:string; attempt_number:number; status:string; tasks:Task[] };
type ApprovalPayload = { current_approval:Attempt|null; approval_history:Attempt[]; can_resubmit:boolean };
const statusLabel:Record<string,string> = { pending:'ממתין', approved:'אושר', rejected:'נדחה', returned:'הוחזר לתיקון', cancelled:'בוטל' };

function AttemptView({ attempt, current, onDecision }:{attempt:Attempt;current?:boolean;onDecision?:(task:Task)=>void}) {
  return <Stack spacing={1}>{attempt.tasks.map(task => <Box key={task.id} sx={{p:1.75,border:'1px solid',borderColor:'divider',borderRadius:2.5,bgcolor:'#fbfcff'}}>
    <Stack direction={{xs:'column',md:'row'}} gap={1.5} alignItems={{md:'center'}}>
      <Box minWidth={150}><Typography variant="caption" color="text.secondary">שלב {task.step_order}</Typography><Typography fontWeight={800}>{task.step_name}</Typography></Box>
      <Box sx={{flex:1}}><Typography variant="caption" color="text.secondary">מאשר</Typography><Typography>{task.approver_name || 'מאשר'}</Typography></Box>
      <Chip label={statusLabel[task.status] || task.status} color={task.status === 'rejected' ? 'error' : task.status === 'approved' ? 'success' : 'default'}/>
      {current && task.can_decide && <Button variant="contained" onClick={() => onDecision?.(task)}>החלטה</Button>}
    </Stack>
    <Typography variant="caption" color="text.secondary">עודכן: {new Date(task.decided_at || task.requested_at).toLocaleString('he-IL')}</Typography>
    {task.comment && <Alert severity={task.status === 'rejected' ? 'error' : 'info'} sx={{mt:1}}>הערה: {task.comment}</Alert>}
  </Box>)}</Stack>;
}

export function CaseApprovalsPanel({caseId}:{caseId:string}) {
  const qc=useQueryClient(); const [selected,setSelected]=useState<Task>(); const [comment,setComment]=useState(''); const [error,setError]=useState(''); const [historyOpen,setHistoryOpen]=useState(false);
  const {data}=useQuery({queryKey:['case-approvals',caseId],queryFn:()=>api<ApprovalPayload>(`/cases/${caseId}/approvals`)});
  const refresh=()=>Promise.all([qc.invalidateQueries({queryKey:['case-approvals',caseId]}),qc.invalidateQueries({queryKey:['case',caseId]}),qc.invalidateQueries({queryKey:['pending-approvals']})]);
  const decision=useMutation({mutationFn:(value:'approved'|'rejected')=>api(`/approval-tasks/${selected!.id}/decision`,{method:'POST',body:JSON.stringify({decision:value,comment:comment.trim()||null})}),onSuccess:async()=>{setSelected(undefined);setComment('');await refresh()},onError:e=>setError((e as Error).message)});
  const resubmit=useMutation({mutationFn:()=>api(`/cases/${caseId}/approvals/resubmit`,{method:'POST'}),onSuccess:refresh,onError:e=>setError((e as Error).message)});
  const current=data?.current_approval;
  return <CaseSection title="אישורים" icon={<FactCheckOutlined/>}>{error&&<Alert severity="error">{error}</Alert>}
    {!current ? <Typography color="text.secondary">לא נדרש תהליך אישור</Typography> : <Stack spacing={2}>
      <Stack direction="row" justifyContent="space-between" alignItems="center"><Typography fontWeight={800}>ניסיון אישור {current.attempt_number}</Typography><Chip label={statusLabel[current.status] || current.status}/></Stack>
      <AttemptView attempt={current} current onDecision={setSelected}/>
      {data?.can_resubmit && <Button variant="contained" onClick={()=>resubmit.mutate()} disabled={resubmit.isPending}>שליחה מחדש לאישור</Button>}
      {!!data?.approval_history.length && <><Button startIcon={<History/>} variant="text" onClick={()=>setHistoryOpen(value=>!value)}>{historyOpen?'הסתרת היסטוריית אישורים':'צפייה בהיסטוריה'}</Button><Collapse in={historyOpen}><Stack spacing={3}>{data.approval_history.map(attempt=><Stack key={attempt.id} spacing={1}><Typography fontWeight={800}>ניסיון {attempt.attempt_number} · {statusLabel[attempt.status] || attempt.status}</Typography><AttemptView attempt={attempt}/></Stack>)}</Stack></Collapse></>}
    </Stack>}
    <Dialog open={!!selected} onClose={()=>setSelected(undefined)} fullWidth><DialogTitle>החלטה בשלב {selected?.step_order}</DialogTitle><DialogContent><TextField sx={{mt:1}} fullWidth multiline label="הערה (חובה בדחייה)" value={comment} onChange={e=>setComment(e.target.value)}/></DialogContent><DialogActions><Button onClick={()=>setSelected(undefined)}>ביטול</Button><Button color="error" disabled={!comment.trim()||decision.isPending} onClick={()=>decision.mutate('rejected')}>דחייה</Button><Button variant="contained" disabled={decision.isPending} onClick={()=>decision.mutate('approved')}>אישור</Button></DialogActions></Dialog>
  </CaseSection>;
}
