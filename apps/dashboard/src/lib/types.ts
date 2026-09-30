export type Role = "owner" | "admin" | "agent";

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  plan: string;
}

export interface MeResponse {
  user: User;
  tenant: Tenant;
}

export interface AuthResponse extends MeResponse {
  csrf_token: string;
  access_token_expires_at: string;
}

export interface SessionInfo {
  id: string;
  created_at: string;
  last_used_at: string;
  expires_at: string;
  user_agent: string;
  ip_address: string;
  current: boolean;
}

export interface AuditEvent {
  id: string;
  actor_user_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  ip_address: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AuditPage {
  items: AuditEvent[];
  next_before: string | null;
}

export const ADMIN_ROLES: readonly Role[] = ["owner", "admin"];
