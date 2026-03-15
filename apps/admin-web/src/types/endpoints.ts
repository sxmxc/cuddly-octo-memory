export type JsonValue = string | number | boolean | null | JsonObject | JsonValue[];

export interface JsonObject {
  [key: string]: JsonValue;
}

export interface AdminUser {
  id: number;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  password_changed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminSession {
  token: string;
  expires_at: string;
  user: AdminUser;
}

export interface AdminSessionSnapshot {
  expires_at: string;
  user: AdminUser;
}

export interface AdminLoginPayload {
  username: string;
  password: string;
  remember_me: boolean;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface AdminUserCreatePayload {
  username: string;
  password: string;
  is_active?: boolean;
  is_superuser?: boolean;
  must_change_password?: boolean;
}

export interface AdminUserUpdatePayload {
  username?: string;
  password?: string;
  is_active?: boolean;
  is_superuser?: boolean;
  must_change_password?: boolean;
}

export interface EndpointPayload {
  name: string;
  slug: string;
  method: string;
  path: string;
  category: string | null;
  tags: string[];
  summary: string | null;
  description: string | null;
  enabled: boolean;
  auth_mode: string;
  request_schema: JsonObject | null;
  response_schema: JsonObject | null;
  success_status_code: number;
  error_rate: number;
  latency_min_ms: number;
  latency_max_ms: number;
  seed_key: string | null;
}

export interface Endpoint extends EndpointPayload {
  id: number;
  created_at: string;
  updated_at: string;
}

export interface EndpointDraft {
  name: string;
  slug: string;
  method: string;
  path: string;
  category: string;
  tags: string;
  summary: string;
  description: string;
  enabled: boolean;
  auth_mode: string;
  request_schema: JsonObject;
  response_schema: JsonObject;
  success_status_code: number;
  error_rate: number;
  latency_min_ms: number;
  latency_max_ms: number;
  seed_key: string;
}

export interface PreviewResponsePayload {
  preview: JsonValue;
}
