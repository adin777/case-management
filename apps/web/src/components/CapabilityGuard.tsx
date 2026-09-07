import { CircularProgress, Stack } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { api } from '../api/client';
import type { User } from '../types';

export function CapabilityGuard({ children }: { children: ReactNode }) {
  const me = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me') });
  if (me.isLoading) return <Stack alignItems="center" py={8}><CircularProgress /></Stack>;
  if (!me.data?.is_system_admin && !me.data?.can_implement) return <Navigate to="/" replace />;
  return children;
}
