import { Alert, FormControlLabel, Paper, Stack, Switch, Typography } from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';

type Settings={field_history_enabled:boolean;core_fields:{field_key:string;track_history:boolean}[]};
const coreLabels:Record<string,string>={title:'נושא',description:'תיאור',request_type:'סוג קריאה',environment:'סביבה',assignee:'מטפל',lock_state:'מצב נעילה'};
export function FieldHistorySettings(){
  const client=useQueryClient();const query=useQuery({queryKey:['field-history-settings'],queryFn:()=>api<Settings>('/system/field-history-settings'),retry:false});
  const save=useMutation({mutationFn:(enabled:boolean)=>api('/system/field-history-settings',{method:'PUT',body:JSON.stringify({field_history_enabled:enabled})}),onSuccess:()=>client.invalidateQueries({queryKey:['field-history-settings']})});
  const saveCore=useMutation({mutationFn:({key,enabled}:{key:string;enabled:boolean})=>api(`/system/core-field-history/${key}`,{method:'PUT',body:JSON.stringify({track_history:enabled})}),onSuccess:()=>client.invalidateQueries({queryKey:['field-history-settings']})});
  if(query.isError)return null;
  return <Paper variant="outlined" sx={{p:2.5}}><Stack spacing={1.5}><Typography variant="h6">היסטוריית שדות</Typography><Typography color="text.secondary">מתג מערכת ראשי. הגדרת המעקב לכל שדה נשמרת גם כשהמתג כבוי.</Typography><FormControlLabel control={<Switch checked={query.data?.field_history_enabled??true} disabled={save.isPending} onChange={event=>save.mutate(event.target.checked)}/>} label="שמירת היסטוריית שינויי שדות"/>{!query.data?.field_history_enabled&&<Alert severity="warning">שינויי שדות חדשים לא יירשמו. Audit עסקי אחר ממשיך לפעול.</Alert>}<Typography fontWeight={800}>שדות ליבה למעקב</Typography><Stack direction="row" flexWrap="wrap" gap={1}>{Object.entries(coreLabels).map(([key,label])=><FormControlLabel key={key} control={<Switch size="small" checked={query.data?.core_fields.some(row=>row.field_key===key&&row.track_history)??false} disabled={saveCore.isPending} onChange={event=>saveCore.mutate({key,enabled:event.target.checked})}/>} label={label}/>)}</Stack></Stack></Paper>;
}
