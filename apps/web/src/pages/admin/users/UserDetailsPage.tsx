import type { Environment, Group, User } from '../../../types';
import { UserEditor } from './UserEditor/UserEditor';

export function UserDetailsPage(props: { user?: User; users: User[]; groups?: Group[]; environments: Environment[]; onClose: () => void; onSaved: () => Promise<void> }) {
  const { data: loadedGroups = [] } = useQuery({ queryKey: ['groups'], queryFn: () => api<Group[]>('/groups'), enabled: !props.groups });
  return <UserEditor {...props} groups={props.groups || loadedGroups}/>;
}
import { useQuery } from '@tanstack/react-query';
import { api } from '../../../api/client';
