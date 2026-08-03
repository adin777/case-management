import { Add, Settings } from '@mui/icons-material';
import { Box, Button, Card, CardContent, Grid, Stack, Typography } from '@mui/material';
import type { Environment } from '../../../types';

export function EnvironmentList({ environments, selected, onSelect, onCreate }: { environments: Environment[]; selected?: Environment; onSelect: (item: Environment) => void; onCreate: () => void }) {
  return <><Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={2}><Box><Typography variant="h4" fontWeight={800}>סביבות עבודה</Typography><Typography color="text.secondary">הגדרת תהליכים, שדות, הרשאות ואוטומציות</Typography></Box><Button variant="contained" startIcon={<Add />} onClick={onCreate}>סביבה חדשה</Button></Stack><Grid container spacing={2}>{environments.map((item) => <Grid size={{ xs: 12, md: 4 }} key={item.id}><Card onClick={() => onSelect(item)} sx={{ cursor: 'pointer', border: selected?.id === item.id ? '2px solid' : undefined, borderColor: 'primary.main' }}><CardContent><Stack direction="row" spacing={1.5}><Settings color="primary"/><Box><Typography variant="h6">{item.name_he}</Typography><Typography color="text.secondary">{item.name_en} · {item.code}</Typography><Typography variant="body2">{item.is_active ? 'פעילה' : 'מושבתת'}</Typography></Box></Stack></CardContent></Card></Grid>)}</Grid></>;
}
