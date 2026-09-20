/**
 * API Client and TanStack Query hooks for WH40k Colony Manager
 * 
 * This module provides:
 * - API client with automatic token refresh using HttpOnly cookies
 * - CSRF token management for state-changing requests
 * - TanStack Query hooks for all backend resources
 * 
 * SECURITY: Uses HttpOnly cookies + CSRF tokens instead of localStorage
 * Per 07-frontend-architecture.md: All server state lives in TanStack Query,
 * and the frontend never reimplements backend rule logic.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  Colony,
  Representative,
  Infrastructure,
  SupportUpgrade,
  Modifier,
  ColonyResource,
  DevelopmentPlan,
  User,
  ColonyStatsBreakdown,
  ColonyType,
  ColonyTypeInfo,
  ModifierStat,
  InfrastructureState,
} from '../types/colony';

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

// ============================================================================
// Types (Backend API Schemas)
// ============================================================================

export interface AuthSession {
  /**
   * The authenticated user. Authentication is carried entirely by HttpOnly
   * cookies + CSRF (per 07-frontend-architecture.md), so no token fields are
   * ever exposed to the frontend.
   */
  user: User | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface ColonyCreate {
  name: string;
  founder_name: string;
  patron_name?: string | null;
  colony_type: ColonyType;
  // Optional founding size for advanced-stage colonies. When omitted the backend
  // falls back to the colony type's default starting size (config/colony_types.yaml).
  base_size?: number | null;
}

export interface ColonyUpdate {
  name?: string | null;
  founder_name?: string | null;
  patron_name?: string | null;
  age_days?: number | null;
  current_event?: string | null;
}

export interface ModifierCreate {
  colony_id: string;
  name: string;
  modifier_stat: ModifierStat;
  modifier_value: number;
  source: string;
  is_active: boolean;
  description?: string | null;
}

export interface ModifierUpdate {
  name?: string;
  modifier_stat?: ModifierStat;
  modifier_value?: number;
  is_active?: boolean;
  description?: string | null;
}

export interface InfrastructureCreate {
  colony_id: string;
  infrastructure_type: string;
  name: string;
  state: InfrastructureState;
  notes?: string | null;
}

export interface SupportUpgradeCreate {
  colony_id: string;
  upgrade_type: string;
  name: string;
  chosen_stat?: ModifierStat | null;
  custom_product?: string | null;
  notes?: string | null;
}

export interface RepresentativeCreate {
  name: string;
  title: string;
  representative_type: string;
  personality: string;
  stat_bonus: number;
  skills?: string[];
  talents?: string[];
  notes?: string | null;
}

export interface DevelopmentPlanCreate {
  colony_id: string;
  name: string;
  category?: 'Hard Infrastructure' | 'Support Upgrade' | 'Specialty Project';
  target_category?: string;
  specific_type?: string;
  target_stat?: ModifierStat;
  target_value?: number;
  priority_rank?: number;
  status?: 'active' | 'in_progress' | 'planning' | 'completed' | 'abandoned';
}

// ============================================================================
// CSRF Token Management
// ============================================================================

/**
 * CSRF token for state-changing requests.
 * Fetched after login and included in POST/PUT/PATCH/DELETE requests.
 */
let csrfToken: string | null = null;

/**
 * Set the CSRF token (called after successful login).
 * @param token - CSRF token from backend
 */
export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

/**
 * Get the current CSRF token.
 * @returns CSRF token or null if not set
 */
export function getCsrfToken(): string | null {
  return csrfToken;
}

/**
 * Clear the CSRF token (called on logout).
 */
export function clearCsrfToken(): void {
  csrfToken = null;
}

// ============================================================================
// API Error Handling
// ============================================================================

export class ApiError extends Error {
  status: number;
  details?: any;

  constructor(status: number, message: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

// ============================================================================
// Core API Client
// ============================================================================

/**
 * In-flight CSRF-token fetch promise so concurrent mutating requests share a
 * single fetch instead of each triggering one (mirrors the 401-refresh mutex).
 */
let csrfTokenPromise: Promise<string> | null = null;

/**
 * Ensure a CSRF token is available, fetching it lazily from the backend when
 * one isn't already cached in memory.
 *
 * The backend also mirrors this value into an HttpOnly cookie, which the
 * browser auto-attaches (via `credentials: 'include'`) to credentialed
 * requests; echoing the body value back as the X-CSRF-Token header satisfies
 * the server-side double-submit check. The cookie is never read from
 * `document.cookie` (HttpOnly blocks it) — the token always comes from this
 * response body.
 *
 * Per 07-frontend-architecture.md this runs before the first mutating request
 * (and on session start), not only at login — the in-memory value resets on a
 * page refresh while the HttpOnly session cookies persist, so without this a
 * state-changing request after refresh would be rejected as "CSRF token
 * missing".
 *
 * @returns The current CSRF token.
 */
async function ensureCsrfToken(): Promise<string> {
  if (csrfToken) {
    return csrfToken;
  }
  if (!csrfTokenPromise) {
    csrfTokenPromise = fetch(`${API_BASE_URL}/auth/csrf-token`, {
      method: 'GET',
      credentials: 'include',
    })
      .then((response) => {
        if (!response.ok) {
          throw new ApiError(response.status, 'Failed to fetch CSRF token');
        }
        return response.json() as Promise<{ csrf_token: string }>;
      })
      .then((data) => {
        csrfToken = data.csrf_token;
        return csrfToken;
      })
      .finally(() => {
        csrfTokenPromise = null;
      });
  }
  return csrfTokenPromise;
}

/**
 * Normalize a request path to an absolute API URL.
 *
 * The API base URL already includes `/api/v1`, so a leading `/api/v1` passed
 * by callers is stripped to avoid doubling it. Absolute http(s) URLs pass
 * through untouched.
 */
function toApiUrl(url: string): string {
  if (url.startsWith('http')) {
    return url;
  }
  let path = url;
  if (path.startsWith('/api/v1')) {
    path = path.slice('/api/v1'.length);
  }
  if (!path.startsWith('/')) {
    path = `/${path}`;
  }
  return `${API_BASE_URL}${path}`;
}

/**
 * Options for the shared request core. Extends fetch's RequestInit with one
 * internal flag consumed by the 401-refresh logic (never spread into fetch).
 */
type ApiRequestOptions = RequestInit & {
  /**
   * True for requests that carry no established session to refresh (login /
   * register). A 401 on those means "credentials rejected", not "session
   * expired": skip the refresh-retry and surface the backend's real message.
   */
  skipAuthRefresh?: boolean;
};


/**
 * Single shared request core used by fetchApi (the TanStack Query hooks) and
 * apiFetch (legacy callers). Attaches credentials, the CSRF header on
 * state-changing methods, and the 401 → refresh → retry-once flow — so all
 * request plumbing lives in exactly one place.
 */
async function apiRequest(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<Response> {
  // skipAuthRefresh is consumed here and never spread into fetch.
  const { skipAuthRefresh = false, ...fetchOptions } = options;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(fetchOptions.headers as HeadersInit),
  };

  // Add CSRF token to state-changing requests
  const method = (fetchOptions.method || 'GET').toUpperCase();
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    (headers as Record<string, string>)['X-CSRF-Token'] = await ensureCsrfToken();
  }

  const response = await fetch(toApiUrl(endpoint), {
    ...fetchOptions,
    headers,
    credentials: 'include', // Send cookies automatically for authentication
  });

  // 401 → the access token may have expired. Attempt a single shared refresh
  // (all concurrent 401s coalesce onto one in-flight /auth/refresh — required
  // because the backend rotates the refresh cookie), then retry the request
  // once with the fresh cookies.
  //
  // Requests flagged skipAuthRefresh (login/register) are exempt: a 401 there
  // is a credential rejection, not an expiry, so refreshing would be wasteful
  // and would mislabel the real error (see the 401 branch in fetchApi).
  if (response.status === 401 && !skipAuthRefresh) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiRequest(endpoint, options);
    }
  }

  return response;
}

/**
 * Typed fetch wrapper with authentication and error handling.
 * Uses HttpOnly cookies for authentication and CSRF tokens for state-changing requests.
 */
async function fetchApi<T>(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const response = await apiRequest(endpoint, options);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));

    // For session-carrying requests, a 401 that already failed refresh is an
    // expired session — surface a standardized message so the shared 401
    // handling (clear session, redirect) can run.
    // Requests flagged skipAuthRefresh (login/register) fall through instead:
    // their 401 is a credential rejection, so the backend's real message
    // (e.g. "Invalid username or password") is preserved rather than
    // mislabeled as a session expiry.
    if (response.status === 401 && !options.skipAuthRefresh) {
      throw new ApiError(
        response.status,
        'Session expired. Please log in again.',
        errorData
      );
    }

    throw new ApiError(
      response.status,
      errorData.detail || errorData.message || `HTTP ${response.status}`,
      errorData
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// ============================================================================
// Authentication Functions
// ============================================================================

/**
 * In-flight refresh promise shared by concurrent 401 handlers. The backend
 * rotates the refresh cookie on every /auth/refresh, so independent concurrent
 * refreshes would race — the first succeeds and the rest fail on the
 * already-rotated token. Coalescing onto one promise avoids that (per
 * 07-frontend-architecture.md).
 */
let refreshTokenPromise: Promise<boolean> | null = null;

/**
 * Perform the actual POST /auth/refresh round-trip.
 * @returns true if refresh succeeded
 */
async function performRefresh(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include', // Send refresh token cookie
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Refresh access token using refresh token cookie.
 * Concurrent callers share a single in-flight refresh promise.
 * @returns true if successful, false otherwise
 */
async function refreshAccessToken(): Promise<boolean> {
  if (!refreshTokenPromise) {
    refreshTokenPromise = performRefresh().finally(() => {
      refreshTokenPromise = null;
    });
  }
  return refreshTokenPromise;
}

/**
 * Login with username and password.
 * Sets HttpOnly cookies and fetches CSRF token on success.
 */
export async function loginApi(username: string, password: string): Promise<AuthSession> {
  // Login sets HttpOnly cookies on the response; the body only carries a
  // success message (no tokens returned, per cookie-only auth). Login carries
  // no established session, so a 401 here is a credential rejection, not an
  // expiry — skip the refresh-retry and surface the backend's real message
  // (skipAuthRefresh).
  await fetchApi<{ message: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
    skipAuthRefresh: true,
  });

  // Fetch current user info (authentication via cookies)
  const user = await fetchApi<User>('/auth/me');

  // Fetch CSRF token for state-changing requests
  const csrfResponse = await fetchApi<{ csrf_token: string }>('/auth/csrf-token');
  setCsrfToken(csrfResponse.csrf_token);

  // Authentication is carried by HttpOnly cookies; the FE only needs the user.
  return { user };
}

/**
 * Register a new user account.
 * Sets HttpOnly cookies and fetches CSRF token on success.
 */
export async function registerApi(data: RegisterRequest): Promise<AuthSession> {
  // Register returns the created user (UserResponse); auth is cookie-based and
  // no tokens are ever returned in the body. Same rationale as login:
  // registration has no session yet, so a 401 there is a rejection (e.g. a
  // duplicate/invalid account), not an expiry.
  const created = await fetchApi<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
    skipAuthRefresh: true,
  });

  // Fetch current user info (authentication via cookies)
  const user = await fetchApi<User>('/auth/me');

  // Fetch CSRF token for state-changing requests
  const csrfResponse = await fetchApi<{ csrf_token: string }>('/auth/csrf-token');
  setCsrfToken(csrfResponse.csrf_token);

  // Authentication is carried by HttpOnly cookies; the FE only needs the user.
  return { user: user ?? created };
}

/**
 * Logout and revoke tokens.
 * Clears CSRF token on completion.
 */
export async function logoutApi(): Promise<void> {
  try {
    await fetchApi('/auth/revoke', {
      method: 'POST',
      body: JSON.stringify({ reason: 'logout' }),
    });
  } catch {
    // Ignore errors on logout - still clear local state
  }
  clearCsrfToken();
}

// ============================================================================
// TanStack Query Hooks - Authentication
// ============================================================================

export function useCurrentUser() {
  return useQuery<User | null, ApiError>({
    queryKey: ['auth', 'me'],
    queryFn: () => fetchApi<User | null>('/auth/me'),
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation<AuthSession, ApiError, LoginRequest>({
    mutationFn: ({ username, password }) => loginApi(username, password),
    onSuccess: () => {
      // Invalidate the current user query so it refetches with the new session
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();

  return useMutation<AuthSession, ApiError, RegisterRequest>({
    mutationFn: registerApi,
    onSuccess: () => {
      // Invalidate the current user query so it refetches with the new session
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logoutApi,
    onSuccess: () => {
      queryClient.clear();
      clearCsrfToken();
    },
  });
}

// ============================================================================
// TanStack Query Hooks - Colonies
// ============================================================================

export function useColonies() {
  return useQuery<Colony[], ApiError>({
    queryKey: ['colonies'],
    queryFn: () => fetchApi<Colony[]>('/colonies'),
    enabled: true, // Auth handled by cookies
  });
}

// Type alias for ID parameters used across multiple hooks
type IdParam = number | string | null;

export function useColony(colonyId: IdParam) {
  return useQuery<Colony, ApiError>({
    queryKey: ['colonies', colonyId],
    queryFn: () => fetchApi<Colony>(`/colonies/${colonyId}`),
    enabled: !!colonyId, // Only fetch if colonyId is provided
  });
}

export function useColonyStats(colonyId: IdParam) {
  return useQuery<ColonyStatsBreakdown, ApiError>({
    queryKey: ['colonies', colonyId, 'stats'],
    queryFn: () => fetchApi<ColonyStatsBreakdown>(`/colonies/${colonyId}/stats`),
    enabled: !!colonyId,
  });
}

export function useCreateColony() {
  const queryClient = useQueryClient();

  return useMutation<Colony, ApiError, ColonyCreate>({
    mutationFn: (data) =>
      fetchApi<Colony>('/colonies', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['colonies'] });
    },
  });
}

export function useUpdateColony(colonyId: IdParam) {
  const queryClient = useQueryClient();

  return useMutation<Colony, ApiError, ColonyUpdate>({
    mutationFn: (data) =>
      fetchApi<Colony>(`/colonies/${colonyId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['colonies', colonyId] });
      queryClient.invalidateQueries({ queryKey: ['colonies'] });
    },
  });
}

export function useDeleteColony() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, IdParam>({
    mutationFn: (colonyId) =>
      fetchApi<void>(`/colonies/${colonyId}`, {
        method: 'DELETE',
      }),
    onSuccess: (_, colonyId) => {
      queryClient.invalidateQueries({ queryKey: ['colonies'] });
      queryClient.removeQueries({ queryKey: ['colonies', colonyId] });
    },
  });
}

// ============================================================================
// TanStack Query Hooks - Representatives
// ============================================================================

export function useRepresentatives(colonyId?: IdParam) {
  const url = colonyId
    ? `/colonies/${colonyId}/representative`
    : '/representatives';

  return useQuery<Representative[] | Representative, ApiError>({
    queryKey: ['representatives', colonyId || 'all'],
    queryFn: () => fetchApi<Representative[] | Representative>(url),
    enabled: true, // Auth handled by cookies
  });
}

export function useCreateRepresentative() {
  const queryClient = useQueryClient();

  return useMutation<Representative, ApiError, RepresentativeCreate>({
    mutationFn: (data) =>
      fetchApi<Representative>('/representatives', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['representatives'] });
    },
  });
}

export function useAssignRepresentative(repId: IdParam) {
  const queryClient = useQueryClient();

  return useMutation<Representative, ApiError, { colony_id: IdParam }>({
    mutationFn: ({ colony_id }) =>
      fetchApi<Representative>(`/representatives/${repId}/assign`, {
        method: 'POST',
        body: JSON.stringify({ colony_id }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['representatives'] });
      queryClient.invalidateQueries({ queryKey: ['colonies'] });
    },
  });
}

export function useUnassignRepresentative() {
  const queryClient = useQueryClient();

  return useMutation<Representative, ApiError, { colony_id: IdParam }>({
    mutationFn: ({ colony_id }) =>
      fetchApi<Representative>(`/colonies/${colony_id}/representative`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['representatives'] });
      queryClient.invalidateQueries({ queryKey: ['colonies'] });
    },
  });
}

// ============================================================================
// TanStack Query Hooks - Infrastructure
// ============================================================================

export function useInfrastructure(colonyId: IdParam) {
  return useQuery<Infrastructure[], ApiError>({
    queryKey: ['infrastructure', colonyId],
    queryFn: () =>
      fetchApi<Infrastructure[]>(`/colonies/${colonyId}/infrastructure`),
    enabled: !!colonyId,
  });
}

export function useCreateInfrastructure() {
  const queryClient = useQueryClient();

  return useMutation<Infrastructure, ApiError, InfrastructureCreate>({
    mutationFn: (data) =>
      fetchApi<Infrastructure>(`/colonies/${data.colony_id}/infrastructure`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['infrastructure', variables.colony_id],
      });
      queryClient.invalidateQueries({ queryKey: ['colonies'] });
    },
  });
}

export function useUpdateInfrastructure(infrastructureId: IdParam) {
  const queryClient = useQueryClient();

  return useMutation<Infrastructure, ApiError, InfrastructureCreate>({
    mutationFn: (data) =>
      fetchApi<Infrastructure>(`/infrastructure/${infrastructureId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({
        queryKey: ['infrastructure', updated.colony_id],
      });
      queryClient.invalidateQueries({ queryKey: ['colonies'] });
    },
  });
}

export function useDeleteInfrastructure() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, IdParam>({
    mutationFn: (infrastructureId) =>
      fetchApi<void>(`/infrastructure/${infrastructureId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['infrastructure'] });
    },
  });
}

// ============================================================================
// TanStack Query Hooks - Support Upgrades
// ============================================================================

export function useSupportUpgrades(colonyId: IdParam) {
  return useQuery<SupportUpgrade[], ApiError>({
    queryKey: ['upgrades', colonyId],
    queryFn: () =>
      fetchApi<SupportUpgrade[]>(`/colonies/${colonyId}/upgrades`),
    enabled: !!colonyId,
  });
}

export function useCreateSupportUpgrade() {
  const queryClient = useQueryClient();

  return useMutation<SupportUpgrade, ApiError, SupportUpgradeCreate>({
    mutationFn: (data) =>
      fetchApi<SupportUpgrade>(`/colonies/${data.colony_id}/upgrades`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['upgrades', variables.colony_id],
      });
      queryClient.invalidateQueries({ queryKey: ['colonies'] });
    },
  });
}

export function useUpdateSupportUpgrade(upgradeId: IdParam) {
  const queryClient = useQueryClient();

  return useMutation<SupportUpgrade, ApiError, SupportUpgradeCreate>({
    mutationFn: (data) =>
      fetchApi<SupportUpgrade>(`/upgrades/${upgradeId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({
        queryKey: ['upgrades', updated.colony_id],
      });
      queryClient.invalidateQueries({ queryKey: ['colonies'] });
    },
  });
}

export function useDeleteSupportUpgrade() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, IdParam>({
    mutationFn: (upgradeId) =>
      fetchApi<void>(`/upgrades/${upgradeId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['upgrades'] });
    },
  });
}


// ============================================================================
// TanStack Query Hooks - Modifiers
// ============================================================================

export function useModifiers(colonyId: IdParam) {
  return useQuery<Modifier[], ApiError>({
    queryKey: ['modifiers', colonyId],
    queryFn: () => fetchApi<Modifier[]>(`/colonies/${colonyId}/modifiers`),
    enabled: !!colonyId,
  });
}

export function useCreateModifier() {
  const queryClient = useQueryClient();

  return useMutation<Modifier, ApiError, ModifierCreate>({
    mutationFn: (data) =>
      fetchApi<Modifier>('/modifiers', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['modifiers', variables.colony_id],
      });
      queryClient.invalidateQueries({ queryKey: ['colonies'] });
    },
  });
}

export function useUpdateModifier(modifierId: IdParam) {
  const queryClient = useQueryClient();

  return useMutation<Modifier, ApiError, ModifierUpdate>({
    mutationFn: (data) =>
      fetchApi<Modifier>(`/modifiers/${modifierId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({
        queryKey: ['modifiers', updated.colony_id],
      });
      queryClient.invalidateQueries({ queryKey: ['colonies'] });
    },
  });
}

export function useDeleteModifier() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, IdParam>({
    mutationFn: (modifierId) =>
      fetchApi<void>(`/modifiers/${modifierId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modifiers'] });
    },
  });
}

// ============================================================================
// TanStack Query Hooks - Resources
// ============================================================================

export function useResources(colonyId: IdParam) {
  return useQuery<ColonyResource[], ApiError>({
    queryKey: ['resources', colonyId],
    queryFn: () => fetchApi<ColonyResource[]>(`/colonies/${colonyId}/resources`),
    enabled: !!colonyId,
  });
}

export function useCreateResource() {
  const queryClient = useQueryClient();

  return useMutation<ColonyResource, ApiError, Omit<ColonyResource, 'id'>>({
    mutationFn: (data) =>
      fetchApi<ColonyResource>('/resources', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['resources', variables.colony_id],
      });
    },
  });
}

export function useUpdateResource(resourceId: IdParam) {
  const queryClient = useQueryClient();

  return useMutation<ColonyResource, ApiError, Omit<ColonyResource, 'id'>>({
    mutationFn: (data) =>
      fetchApi<ColonyResource>(`/resources/${resourceId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({
        queryKey: ['resources', updated.colony_id],
      });
    },
  });
}

export function useDeleteResource() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, IdParam>({
    mutationFn: (resourceId) =>
      fetchApi<void>(`/resources/${resourceId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resources'] });
    },
  });
}

// ============================================================================
// TanStack Query Hooks - Development Plans
// ============================================================================

export function useDevelopmentPlans(colonyId: IdParam) {
  return useQuery<DevelopmentPlan[], ApiError>({
    queryKey: ['plans', colonyId],
    queryFn: () =>
      fetchApi<DevelopmentPlan[]>(`/colonies/${colonyId}/development-plans`),
    enabled: !!colonyId,
  });
}

export function useCreateDevelopmentPlan() {
  const queryClient = useQueryClient();

  return useMutation<DevelopmentPlan, ApiError, DevelopmentPlanCreate>({
    mutationFn: (data) =>
      fetchApi<DevelopmentPlan>('/development-plans', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['plans', variables.colony_id],
      });
    },
  });
}

export function useUpdateDevelopmentPlan(planId: IdParam) {
  const queryClient = useQueryClient();

  return useMutation<DevelopmentPlan, ApiError, Partial<DevelopmentPlanCreate>>({
    mutationFn: (data) =>
      fetchApi<DevelopmentPlan>(`/development-plans/${planId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({
        queryKey: ['plans', updated.colony_id],
      });
    },
  });
}

export function useDeleteDevelopmentPlan() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, IdParam>({
    mutationFn: (planId) =>
      fetchApi<void>(`/development-plans/${planId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plans'] });
    },
  });
}

export function useInstallDevelopmentPlan() {
  const queryClient = useQueryClient();

  return useMutation<
    DevelopmentPlan,
    ApiError,
    { planId: IdParam; install_as_infrastructure?: boolean }
  >({
    mutationFn: ({ planId, install_as_infrastructure }) =>
      fetchApi<DevelopmentPlan>(`/development-plans/${planId}/install`, {
        method: 'POST',
        body: JSON.stringify({ install_as_infrastructure }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plans'] });
      queryClient.invalidateQueries({ queryKey: ['infrastructure'] });
      queryClient.invalidateQueries({ queryKey: ['upgrades'] });
    },
  });
}

// ============================================================================
// TanStack Query Hooks - Config (Rule Tables)
// ============================================================================

export function useColonyTypes() {
  return useQuery<ColonyTypeInfo[], ApiError>({
    queryKey: ['config', 'colony-types'],
    queryFn: () => fetchApi<ColonyTypeInfo[]>('/config/colony-types'),
  });
}

export function useInfrastructureTypes() {
  return useQuery<
    { type: string; name: string; description: string; effects: Record<string, number> }[],
    ApiError
  >({
    queryKey: ['config', 'infrastructure-types'],
    queryFn: () =>
      fetchApi<
        { type: string; name: string; description: string; effects: Record<string, number> }[]
      >('/config/infrastructure-types'),
  });
}

export function useSupportUpgradeTypes() {
  return useQuery<
    { type: string; name: string; description: string; stat_options: ModifierStat[] }[],
    ApiError
  >({
    queryKey: ['config', 'support-upgrades'],
    queryFn: () =>
      fetchApi<
        { type: string; name: string; description: string; stat_options: ModifierStat[] }[]
      >('/config/support-upgrades'),
  });
}

export function useRepresentativeTypes() {
  return useQuery<
    { type: string; name: string; description: string }[],
    ApiError
  >({
    queryKey: ['config', 'representative-types'],
    queryFn: () =>
      fetchApi<{ type: string; name: string; description: string }[]>(
        '/config/representative-types'
      ),
  });
}

// ============================================================================
// Legacy API Fetch
// Returns a Response for existing callers. Shares the same request core
// (apiRequest) as fetchApi, so credentials/CSRF/401-refresh are identical.
// New code should use the TanStack Query hooks instead.
// ============================================================================

export const apiFetch = async (url: string, options?: RequestInit): Promise<Response> =>
  apiRequest(url, options);
