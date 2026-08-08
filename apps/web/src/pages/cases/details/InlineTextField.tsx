import { useEffect, useState } from 'react';
import { Box, CircularProgress, TextField, Typography } from '@mui/material';

export function InlineTextField({ label, value, editable, multiline = false, onSave }: {
  label: string; value: string; editable: boolean; multiline?: boolean;
  onSave: (value: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState(value);
  const [state, setState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  useEffect(() => setDraft(value), [value]);
  async function save() {
    const next = draft.trim();
    if (!next || next === value) return;
    setState('saving');
    try { await onSave(next); setState('saved'); }
    catch { setState('error'); setDraft(value); }
  }
  if (!editable) return <Box><Typography variant="caption" color="text.secondary">{label}</Typography><Typography sx={{ whiteSpace: 'pre-wrap' }}>{value || '—'}</Typography></Box>;
  return <Box>
    <TextField fullWidth variant="standard" label={label} value={draft} multiline={multiline}
      minRows={multiline ? 3 : undefined} onChange={(event) => { setDraft(event.target.value); setState('idle'); }}
      onBlur={save} onKeyDown={(event) => {
        if (event.key === 'Escape') { setDraft(value); (event.target as HTMLElement).blur(); }
        if (!multiline && event.key === 'Enter') (event.target as HTMLElement).blur();
      }} />
    <Typography variant="caption" color={state === 'error' ? 'error' : 'text.secondary'}>
      {state === 'saving' && <><CircularProgress size={10}/> שומר...</>}{state === 'saved' && 'נשמר'}{state === 'error' && 'שגיאה בשמירה'}
    </Typography>
  </Box>;
}
