import type { AccessLevel } from './AccessLevelSelector';
export type AccessDomain = { code:string; name_he:string; description_he:string; localized_name?:string; localized_description?:string; scope:string };
export type MatrixRow = {domain_code:string;domain_name:string;description?:string;default_level:AccessLevel;direct_level:AccessLevel;effective_level:AccessLevel;source:string;scope:string;can_override:boolean};
