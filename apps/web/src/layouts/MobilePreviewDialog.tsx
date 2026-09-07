import { Close, PhoneIphone } from '@mui/icons-material';
import { Box, Dialog, DialogContent, DialogTitle, IconButton, MenuItem, Stack, TextField, Tooltip } from '@mui/material';
import { useMemo, useState } from 'react';

const widths = [375, 390, 430] as const;

export function MobilePreviewDialog({ open, onClose, path }: { open: boolean; onClose: () => void; path: string }) {
  const [width, setWidth] = useState<(typeof widths)[number]>(390);
  const source = useMemo(() => { const url = new URL(path, window.location.origin); url.searchParams.set('mobilePreview', '1'); return `${url.pathname}${url.search}${url.hash}`; }, [path]);
  return <Dialog open={open} onClose={onClose} fullScreen><DialogTitle><Stack direction="row" alignItems="center" gap={1}><PhoneIphone /><Box flex={1}>תצוגה מקדימה למובייל</Box><TextField select size="small" label="רוחב" value={width} onChange={(event) => setWidth(Number(event.target.value) as (typeof widths)[number])}>{widths.map((option) => <MenuItem key={option} value={option}>{option}px</MenuItem>)}</TextField><Tooltip title="סגירה"><IconButton onClick={onClose}><Close /></IconButton></Tooltip></Stack></DialogTitle><DialogContent sx={{ bgcolor: '#e8edf5', display: 'flex', justifyContent: 'center', p: 2 }}><Box component="iframe" title="תצוגה מקדימה למובייל" src={source} sx={{ width, height: 'calc(100vh - 96px)', border: '1px solid #aeb9c8', borderRadius: 3, bgcolor: 'white', boxShadow: 8 }} /></DialogContent></Dialog>;
}
