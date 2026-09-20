export function isNavigationActive(pathname: string, target: string): boolean {
  if (target === '/') return pathname === '/' || pathname === '/portal';
  if (target === '/implementer') return pathname === target || pathname.startsWith('/admin/');
  return pathname === target || pathname.startsWith(`${target}/`);
}
