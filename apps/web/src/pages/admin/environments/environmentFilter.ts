import type { Environment } from '../../../types';

export const filterEnvironments = (items: Environment[], activeOnly: boolean) =>
  activeOnly ? items.filter((item) => item.is_active) : items;
