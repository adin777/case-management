import { Close, OpenInNew, Send } from '@mui/icons-material';
import { Alert, Box, Button, CircularProgress, Drawer, IconButton, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import { BusinessPill } from '../../components/BusinessPill';
import type { Case, User } from '../../types';
import { displayCaseNumber } from '../cases/details/caseDisplay';

type Option={id:string;label:string};
export function CaseQuickPreview({caseId,onClose}:{caseId?:string;onClose:()=>void}){
  const client=useQueryClient();const[comment,setComment]=useState('');const item=useQuery({queryKey:['case-quick-preview',caseId],queryFn:()=>api<Case>(`/cases/${caseId}`),enabled:Boolean(caseId)});
  const statuses=useQuery({queryKey:['case-quick-statuses',caseId],queryFn:()=>api<Option[]>(`/cases/${caseId}/allowed-transitions`),enabled:Boolean(caseId&&item.data?.permissions.can_change_status)});
  const assignees=useQuery({queryKey:['case-quick-assignees',item.data?.environment_id],queryFn:()=>api<User[]>(`/environments/${item.data?.environment_id}/eligible-assignees`),enabled:Boolean(item.data?.permissions.can_assign)});
  const refresh=async()=>{await Promise.all([client.invalidateQueries({queryKey:['case-quick-preview',caseId]}),client.invalidateQueries({queryKey:['workspace-cases']})])};
  const change=useMutation({mutationFn:({path,body}:{path:string;body:unknown})=>api(`/cases/${caseId}/${path}`,{method:'POST',body:JSON.stringify(body)}),onSuccess:refresh});
  return <Drawer anchor="left" open={Boolean(caseId)} onClose={onClose} PaperProps={{sx:{width:{xs:'100%',sm:440},p:2}}}><Stack direction="row" alignItems="center"><Typography variant="h5" flex={1}>תצוגה מהירה</Typography><IconButton onClick={onClose}><Close/></IconButton></Stack>{item.isLoading?<Box textAlign="center" py={8}><CircularProgress/></Box>:item.error?<Alert severity="error">טעינת הקריאה נכשלה</Alert>:item.data&&<Stack spacing={2} mt={2}><Box><Typography color="primary" fontWeight={650}>{displayCaseNumber(item.data.case_number)}</Typography><Typography variant="h5">{item.data.title}</Typography></Box><Stack direction="row" gap={1}><BusinessPill label={item.data.status_label||item.data.status}/><BusinessPill label={item.data.priority_label||item.data.priority} kind="priority"/></Stack><Typography sx={{whiteSpace:'pre-wrap'}}>{item.data.description}</Typography>{item.data.permissions.can_change_status&&<TextField select label="שינוי סטטוס" value="" onChange={event=>change.mutate({path:'transitions',body:{workflow_status_id:event.target.value,comment:null}})}>{statuses.data?.map(option=><MenuItem key={option.id} value={option.id}>{option.label}</MenuItem>)}</TextField>}{item.data.permissions.can_assign&&<TextField select label="שיוך מטפל" value={item.data.assignee_id||''} onChange={event=>change.mutate({path:'assign',body:{assignee_id:event.target.value||null,version:item.data?.version}})}><MenuItem value="">ללא מטפל</MenuItem>{assignees.data?.map(user=><MenuItem key={user.id} value={user.id}>{user.display_name}</MenuItem>)}</TextField>}<TextField multiline minRows={3} label="תגובה ציבורית" value={comment} onChange={event=>setComment(event.target.value)}/><Button variant="contained" startIcon={<Send/>} disabled={!comment.trim()} onClick={()=>change.mutate({path:'comments',body:{body:comment.trim(),visibility:'public'}})}>שליחת תגובה</Button><Button component={Link} to={`/cases/${item.data.id}`} startIcon={<OpenInNew/>}>פתיחת פרטי הקריאה</Button></Stack>}</Drawer>;
}
