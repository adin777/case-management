import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert, Box, CircularProgress } from '@mui/material';
import { api } from '../../../../api/client';
import type { Environment } from '../../../../types';
import { SystemFieldCard } from './SystemFieldCard';
import { SystemFieldValuesDialog } from './SystemFieldValuesDialog';
import type { SystemField } from './types';

const visible = new Set(['request_type']);
export function SystemFieldsTab({ environment }: { environment: Environment }) {
  const [selected, setSelected] = useState<SystemField>();
  const { data, isLoading, error } = useQuery({ queryKey: ['system-fields', environment.id], queryFn: () => api<SystemField[]>(`/environments/${environment.id}/system-fields`) });
  if (isLoading) return <CircularProgress/>;
  if (error) return <Alert severity="error">{(error as Error).message}</Alert>;
  return <><Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 2 }}>{data?.filter((field) => visible.has(field.code)).map((field) => <SystemFieldCard key={field.code} field={field} onManage={() => setSelected(field)}/>)}</Box><SystemFieldValuesDialog environment={environment} field={selected} onClose={() => setSelected(undefined)}/></>;
}
