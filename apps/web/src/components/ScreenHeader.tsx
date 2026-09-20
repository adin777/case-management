import type { ReactNode } from 'react';
import { Box, Stack, Typography } from '@mui/material';

export function ScreenHeader({ title, subtitle, action }: { title: string; subtitle: string; action?: ReactNode }) {
  return <Stack className="screen-header" direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={2}>
    <Box><Typography component="h1" variant="h4">{title}</Typography><Typography color="text.secondary" mt={.75}>{subtitle}</Typography></Box>
    {action}
  </Stack>;
}
