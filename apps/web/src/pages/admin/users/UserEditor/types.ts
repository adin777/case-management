export type PermissionDomain = { code: string; name_he: string; description_he: string; category: string; scope: 'global' | 'environment' | 'both' };
export type EffectiveAccess = { domain: string; domain_name: string; effective_level: 'none' | 'view' | 'edit'; source_type: string; source_id?: string; source_name: string; scope: string; resolution_steps: { source_type?: string; source_name?: string; level: string; scope?: string }[] };
export const levelLabel = { inherit: 'ירושה', none: 'ללא', view: 'צפייה', edit: 'עריכה' } as const;
