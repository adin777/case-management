import { useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField } from '@mui/material';

export function CaseLockDialog({ open, locked, onClose, onSave }: { open: boolean; locked: boolean; onClose: () => void; onSave: (reason: string) => Promise<void> }) {
  const [reason, setReason] = useState('');
  return <Dialog open={open} onClose={onClose} fullWidth><DialogTitle>{locked ? 'פתיחת הקריאה לעריכה' : 'נעילת הקריאה לשינויים'}</DialogTitle><DialogContent>{locked ? <Alert severity="info">פתיחת הנעילה תחזיר למשתמשים המורשים את אפשרות העריכה.</Alert> : <TextField autoFocus fullWidth multiline minRows={3} sx={{ mt: 1 }} label="סיבת הנעילה" value={reason} onChange={(e) => setReason(e.target.value)}/>}</DialogContent><DialogActions><Button onClick={onClose}>ביטול</Button><Button variant="contained" color={locked ? 'primary' : 'warning'} disabled={!locked && !reason.trim()} onClick={() => onSave(reason)}>{locked ? 'פתיחת נעילה' : 'נעילה'}</Button></DialogActions></Dialog>;
}
