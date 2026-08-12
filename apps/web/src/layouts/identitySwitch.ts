import type { QueryClient } from '@tanstack/react-query';
import { token } from '../api/client';
export function applyIdentityToken(accessToken:string, client:QueryClient){token.setAccess(accessToken);client.clear()}
