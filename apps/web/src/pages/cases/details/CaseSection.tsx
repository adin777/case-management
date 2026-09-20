import type { ReactNode } from 'react';
import { Box, Card, CardContent, Stack, Typography } from '@mui/material';

export function CaseSection({ title, icon, action, children, id }: { title: string; icon?: ReactNode; action?: ReactNode; children: ReactNode; id?: string }) {
  return <Card id={id} sx={{ borderRadius: '12px', overflow: 'visible' }}>
    <CardContent sx={{ p: { xs: 2, md: 3 }, '&:last-child': { pb: { xs: 2, md: 3 } } }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" gap={2} mb={2.5}>
        <Stack direction="row" alignItems="center" gap={1.25}>
          {icon && <Box sx={{ width: 38, height: 38, display: 'grid', placeItems: 'center', borderRadius: '8px', bgcolor: 'primary.light', color: 'primary.dark' }}>{icon}</Box>}
          <Typography variant="h6">{title}</Typography>
        </Stack>
        {action}
      </Stack>
      {children}
    </CardContent>
  </Card>;
}
