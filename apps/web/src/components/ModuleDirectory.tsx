import type { ReactNode } from 'react';
import { ArrowBack, ArrowForward } from '@mui/icons-material';
import { Box, CardActionArea, Stack, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';

export type DirectoryItem = { id: string; title: string; description: string; icon: ReactNode; detail?: ReactNode; onOpen: () => void };
export function ModuleDirectory({ items }: { items: DirectoryItem[] }) {
  const { i18n } = useTranslation();
  return <Box className="module-directory">{items.map(item => <CardActionArea key={item.id} className="module-directory-row" onClick={item.onOpen}>
    <Box className="permission-module-icon">{item.icon}</Box>
    <Box className="module-directory-copy"><Typography component="h2" variant="h6">{item.title}</Typography><Typography variant="body2" color="text.secondary" mt={.5}>{item.description}</Typography></Box>
    <Stack direction="row" alignItems="center" gap={1} flexWrap="wrap">{item.detail}{i18n.language === 'en' ? <ArrowForward fontSize="small" color="action" /> : <ArrowBack fontSize="small" color="action" />}</Stack>
  </CardActionArea>)}</Box>;
}
