import { WarningAmberOutlined } from '@mui/icons-material';
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from '@mui/material';
import { useState } from 'react';

export type ImpersonationStatus={active:boolean;can_start:boolean;real_actor_name?:string;impersonated_user_name?:string};
export function ImpersonationBanner({status,onEnd}:{status:ImpersonationStatus;onEnd:()=>Promise<void>}){
  const[confirm,setConfirm]=useState(false);const[ending,setEnding]=useState(false);
  if(!status.active)return null;
  const finish=async()=>{setEnding(true);try{await onEnd();setConfirm(false)}finally{setEnding(false)}};
  return <><Box className="impersonation-banner" role="status"><Stack direction={{xs:'column',sm:'row'}} alignItems={{sm:'center'}} gap={1.5}><WarningAmberOutlined/><Box flex={1}><Typography fontWeight={900}>מצב התחזות פעיל</Typography><Typography variant="body2">משתמש מקורי: {status.real_actor_name} · פועל כעת בתור: {status.impersonated_user_name}</Typography></Box><Button variant="contained" color="warning" onClick={()=>setConfirm(true)}>חזרה למשתמש המקורי</Button></Stack></Box><Dialog open={confirm} onClose={()=>setConfirm(false)} fullWidth maxWidth="xs"><DialogTitle>סיום התחזות</DialogTitle><DialogContent><Typography>אתה עומד לסיים התחזות ולחזור לחשבון המקורי.</Typography></DialogContent><DialogActions><Button onClick={()=>setConfirm(false)}>ביטול</Button><Button variant="contained" color="warning" disabled={ending} onClick={finish}>{ending?'חוזר…':'סיום התחזות'}</Button></DialogActions></Dialog></>;
}
