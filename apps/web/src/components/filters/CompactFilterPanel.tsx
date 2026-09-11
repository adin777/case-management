import { ExpandMore, Tune } from '@mui/icons-material';
import { Badge, Box, Button, Collapse, Drawer, Paper, Stack, useMediaQuery, useTheme } from '@mui/material';
import { ReactNode, useState } from 'react';

type Props={primary:ReactNode;advanced?:ReactNode;actions?:ReactNode;activeCount:number;onReset:()=>void};
export function CompactFilterPanel({primary,advanced,actions,activeCount,onReset}:Props){
  const mobile=useMediaQuery(useTheme().breakpoints.down('md'));const[open,setOpen]=useState(false);const[more,setMore]=useState(false);
  const content=<Stack spacing={1}><Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,minmax(0,1fr))',lg:'repeat(6,minmax(0,1fr))'},gap:1,'& .MuiInputBase-root':{minHeight:40}}}>{primary}</Box>{advanced&&<><Button size="small" endIcon={<ExpandMore sx={{transform:more?'rotate(180deg)':'none'}}/>} onClick={()=>setMore(value=>!value)} sx={{alignSelf:'flex-start'}}>מסננים נוספים</Button><Collapse in={more}><Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,minmax(0,1fr))',lg:'repeat(6,minmax(0,1fr))'},gap:1,'& .MuiInputBase-root':{minHeight:40}}}>{advanced}</Box></Collapse></>}<Stack direction="row" gap={1} flexWrap="wrap">{actions}<Button size="small" onClick={onReset}>איפוס</Button></Stack></Stack>;
  if(mobile)return <><Badge badgeContent={activeCount} color="primary"><Button variant="outlined" startIcon={<Tune/>} onClick={()=>setOpen(true)}>סינון</Button></Badge><Drawer anchor="bottom" open={open} onClose={()=>setOpen(false)} PaperProps={{sx:{borderRadius:'20px 20px 0 0',maxHeight:'88vh',p:2}}}><Box sx={{overflowY:'auto'}}>{content}</Box><Button variant="contained" sx={{mt:1}} onClick={()=>setOpen(false)}>הצגת תוצאות</Button></Drawer></>;
  return <Paper variant="outlined" sx={{p:1.5}}>{content}</Paper>;
}
