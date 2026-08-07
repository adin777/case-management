import { Card, CardContent, Chip, Divider, Grid, Typography } from '@mui/material';
import type { Case } from '../../../types';

const labels: Record<string, string> = { not_started: 'לא הוגדר', on_track: 'תקין', warning: 'מתקרב ליעד', breached: 'בחריגה', met: 'היעד הושג' };
const colors: Record<string, 'default' | 'success' | 'warning' | 'error'> = { not_started: 'default', on_track: 'success', warning: 'warning', breached: 'error', met: 'success' };
const date = (value?: string) => value ? new Date(value).toLocaleString('he-IL') : 'לא הוגדר';

export function CaseSlaPanel({ item }: { item: Case }) {
  return <Card variant="outlined"><CardContent><Typography variant="h6" fontWeight={800}>זמני טיפול</Typography><Divider sx={{ my: 1.5 }} /><Grid container spacing={2}><Grid size={{ xs: 12, sm: 6 }}><Typography variant="caption">יעד לתגובה</Typography><Typography>{date(item.response_due_at)}</Typography><Chip size="small" label={labels[item.sla_response_status] || 'לא הוגדר'} color={colors[item.sla_response_status] || 'default'} /></Grid><Grid size={{ xs: 12, sm: 6 }}><Typography variant="caption">יעד לפתרון</Typography><Typography>{date(item.resolution_due_at)}</Typography><Chip size="small" label={labels[item.sla_resolution_status] || 'לא הוגדר'} color={colors[item.sla_resolution_status] || 'default'} /></Grid><Grid size={{ xs: 12, sm: 6 }}><Typography variant="caption">תגובה ראשונה</Typography><Typography>{date(item.first_response_at)}</Typography></Grid><Grid size={{ xs: 12, sm: 6 }}><Typography variant="caption">מועד פתרון</Typography><Typography>{date(item.resolved_at)}</Typography></Grid></Grid></CardContent></Card>;
}
