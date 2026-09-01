import { useState } from 'react';
import { ContentCopy, EditOutlined, Lock, LockOpen, MoreHoriz, SwapHoriz } from '@mui/icons-material';
import { Button, Chip, Divider, IconButton, Menu, MenuItem, Paper, Stack, Typography } from '@mui/material';
import type { Case } from '../../../types';
import { displayCaseNumber, formatCaseDate } from './caseDisplay';
import { MobileActionBar } from '../../../components/responsive/ResponsivePrimitives';

type HeaderCase = Case & { environment_name?: string };

export function CaseDetailsHeader({ item, status, priority, onEdit, onLock, onTransfer }: { item: HeaderCase; status: string; priority?: string; onEdit: () => void; onLock: () => void; onTransfer: () => void }) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const number = displayCaseNumber(item.case_number);
  return <Paper className="case-details-hero" elevation={0}>
    <Stack direction={{ xs: 'column', lg: 'row' }} justifyContent="space-between" gap={3}>
      <Stack spacing={1.5} minWidth={0}>
        <Stack direction="row" alignItems="center" gap={1.25} flexWrap="wrap">
          <Typography className="case-number">{number}</Typography>
          <Chip className="status-pill" color="primary" label={status}/>
          {priority && <Chip className="status-pill" color="warning" variant="outlined" label={priority}/>}
          {item.is_locked && <Chip color="warning" icon={<Lock/>} label="נעולה לשינויים"/>}
          <Chip variant="outlined" label={item.environment_name || 'סביבה לא זמינה'}/>
        </Stack>
        <Typography variant="h4" sx={{ overflowWrap: 'anywhere' }}>{item.title}</Typography>
        <Stack direction={{ xs: 'column', sm: 'row' }} gap={{ xs: .75, sm: 2.5 }} divider={<Divider orientation="vertical" flexItem/>} color="text.secondary">
          <Typography variant="body2"><strong>פותח הקריאה:</strong> {item.reporter_name || 'לא זמין'}</Typography>
          <Typography variant="body2"><strong>נפתחה:</strong> {formatCaseDate(item.created_at)}</Typography>
          <Typography variant="body2"><strong>עדכון אחרון:</strong> {formatCaseDate(item.updated_at)}</Typography>
        </Stack>
      </Stack>
      <Stack direction="row" gap={1} alignItems="flex-start" flexWrap="wrap" sx={{display:{xs:'none',md:'flex'}}}>
        {item.permissions.can_edit && <Button variant="contained" startIcon={<EditOutlined/>} onClick={onEdit}>עריכה</Button>}
        {item.permissions.can_lock && <Button variant="outlined" color={item.is_locked ? 'success' : 'warning'} startIcon={item.is_locked ? <LockOpen/> : <Lock/>} onClick={onLock}>{item.is_locked ? 'שחרור נעילה' : 'נעילה'}</Button>}
        {item.permissions.can_transfer && <Button variant="outlined" startIcon={<SwapHoriz/>} onClick={onTransfer}>העברה</Button>}
        <IconButton aria-label="פעולות נוספות" onClick={(event) => setAnchor(event.currentTarget)} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}><MoreHoriz/></IconButton>
        <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
          <MenuItem onClick={async () => { await navigator.clipboard.writeText(number); setAnchor(null); }}><ContentCopy fontSize="small" sx={{ ml: 1 }}/>העתקת מספר קריאה</MenuItem>
        </Menu>
      </Stack>
    </Stack>
    <MobileActionBar>{item.permissions.can_edit&&<Button variant="contained" onClick={onEdit}>עריכה</Button>}{item.permissions.can_lock&&<Button variant="outlined" onClick={onLock}>{item.is_locked?'שחרור':'נעילה'}</Button>}<Button variant="outlined" onClick={(event)=>setAnchor(event.currentTarget)}>פעולות נוספות</Button></MobileActionBar>
  </Paper>;
}
