import { Button, Paper, Stack, Typography } from '@mui/material';
import type { SystemField } from './types';

export function SystemFieldCard({ field, onManage }: { field: SystemField; onManage: () => void }) {
  return <Paper variant="outlined" sx={{ p: 2 }}><Stack spacing={1}>
    <Typography variant="h6" fontWeight={800}>{field.label_he}</Typography>
    <Typography color="text.secondary">{field.description_he}</Typography>
    <Typography variant="body2">{field.active_option_count} ערכים פעילים</Typography>
    <Button variant="outlined" onClick={onManage}>ניהול ערכים</Button>
  </Stack></Paper>;
}
