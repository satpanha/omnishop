// ─── OmniShop TMA — Typed API Client ───

const API_URL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_BASE = `${API_URL}/api/v1`;

// ─── Interfaces ───

// ── OmniBot: Orders ──────────────────────────────────────────────────────────

export type OrderStatus =
  | 'awaiting_payment'
  | 'paid'
  | 'preparing'
  | 'dispatched'
  | 'delivered'
  | 'cancelled'
  | 'payment_expired';

export type PaymentStatus = 'initiated' | 'paid' | 'failed' | 'expired';

export interface PaymentInfo {
  id: string;
  provider: string;
  amount: string;
  currency: string;
  khqr_string: string | null;
  aba_link: string | null;
  provider_txn_ref: string | null;
  status: PaymentStatus;
  paid_at: string | null;
}

export interface OrderLineItem {
  id: string;
  product_id: string;
  quantity: number;
  total_price: string;
}

export interface Order {
  id: string;
  seller_id: string;
  buyer_platform: string;
  buyer_id: string;
  total_amount: string;
  currency: string;
  status: OrderStatus;
  delivery_address: string | null;
  delivery_lat: string | null;
  delivery_lng: string | null;
  distance_km: string | null;
  eta_minutes: number | null;
  dispatch_at: string | null;
  created_at: string;
  updated_at: string;
  line_items: OrderLineItem[];
  payment: PaymentInfo | null;
}

export interface OrderList {
  items: Order[];
  total: number;
}

export interface DeliveryLocation {
  lat: number;
  lng: number;
  address?: string;
}

export interface CreateOrderPayload {
  items: { product_id: string; quantity: number }[];
  delivery?: DeliveryLocation;
  idempotency_key?: string;
}

export interface UpdateOrderStatusPayload {
  status: OrderStatus;
  eta_minutes?: number;
  dispatch_at?: string;
}

// ── OmniBot: Conversations ────────────────────────────────────────────────────

export type ConversationState = 'bot' | 'awaiting_owner' | 'owner_handling' | 'closed';

export interface Message {
  id: string;
  conversation_id: string;
  direction: 'inbound' | 'outbound';
  sender: 'buyer' | 'owner' | 'bot';
  text: string;
  telegram_message_id: string | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  buyer_platform: string;
  buyer_id: string;
  state: ConversationState;
  last_message_at: string | null;
  messages?: Message[];
}

export interface ConversationList {
  items: Conversation[];
  total: number;
}

// ── Products ──────────────────────────────────────────────────────────────────

export interface Product {
  id: string;
  seller_id: string;
  name: string;
  description: string;
  price: number;
  stock_quantity: number;
  image_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: string;
  product_id: string;
  buyer_platform: string;
  buyer_id: string;
  quantity: number;
  total_price: number;
  status: 'pending' | 'paid' | 'cancelled';
  created_at: string;
}

export interface UserInfo {
  telegram_id: number;
  first_name: string;
  last_name: string | null;
  username: string | null;
  is_admin: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

export interface ApiError {
  detail: string;
  status: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProductQueryParams {
  search?: string;
  limit?: number;
  offset?: number;
}

export interface CreateProductPayload {
  name: string;
  description: string;
  price: number;
  stock_quantity: number;
  image_url?: string;
  is_active?: boolean;
}

export interface UpdateProductPayload extends Partial<CreateProductPayload> {}

// ─── Token Management ───

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
  if (token) {
    try {
      localStorage.setItem('omnishop-token', token);
    } catch {
      // localStorage not available
    }
  } else {
    try {
      localStorage.removeItem('omnishop-token');
    } catch {
      // localStorage not available
    }
  }
}

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  try {
    authToken = localStorage.getItem('omnishop-token');
  } catch {
    // localStorage not available
  }
  return authToken;
}

// ─── API Client ───

class ApiClientError extends Error {
  public status: number;
  public detail: string;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.detail = message;
  }
}

async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include',
    });

    if (!response.ok) {
      let errorMessage = `API Error: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        // Could not parse error body
      }
      throw new ApiClientError(errorMessage, response.status);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    const data: T = await response.json();
    return data;
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    throw new ApiClientError(
      error instanceof Error ? error.message : 'Network error',
      0
    );
  }
}

// ─── Product API ───

export async function getProducts(
  params?: ProductQueryParams
): Promise<PaginatedResponse<Product>> {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set('search', params.search);
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));

  const query = searchParams.toString();
  const endpoint = `/products${query ? `?${query}` : ''}`;
  return apiClient<PaginatedResponse<Product>>(endpoint);
}

export async function getProduct(id: string): Promise<Product> {
  return apiClient<Product>(`/products/${id}`);
}

export async function createProduct(
  data: CreateProductPayload
): Promise<Product> {
  return apiClient<Product>('/products', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateProduct(
  id: string,
  data: UpdateProductPayload
): Promise<Product> {
  return apiClient<Product>(`/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteProduct(id: string): Promise<void> {
  return apiClient<void>(`/products/${id}`, {
    method: 'DELETE',
  });
}

/**
 * Upload a product photo and return its public URL.
 * Sends multipart/form-data — the browser sets the Content-Type boundary, so we
 * must not set it manually (hence a dedicated fetch rather than apiClient).
 */
export async function uploadProductImage(file: File): Promise<{ url: string }> {
  const form = new FormData();
  form.append('file', file);

  const headers: Record<string, string> = {};
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/products/upload-image`, {
      method: 'POST',
      body: form,
      headers,
      credentials: 'include',
    });
  } catch (error) {
    throw new ApiClientError(
      error instanceof Error ? error.message : 'Network error',
      0
    );
  }

  if (!response.ok) {
    let errorMessage = `Upload failed: ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
    } catch {
      // Could not parse error body
    }
    throw new ApiClientError(errorMessage, response.status);
  }

  return response.json();
}

// ─── Transaction API ───

export async function createTransaction(
  productId: string,
  quantity: number
): Promise<Transaction> {
  return apiClient<Transaction>('/transactions', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId, quantity }),
  });
}

export async function getTransactions(
  params?: { status?: string; limit?: number; offset?: number }
): Promise<PaginatedResponse<Transaction>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));

  const query = searchParams.toString();
  const endpoint = `/transactions${query ? `?${query}` : ''}`;
  return apiClient<PaginatedResponse<Transaction>>(endpoint);
}

export async function updateTransactionStatus(
  id: string,
  status: 'pending' | 'paid' | 'cancelled'
): Promise<Transaction> {
  return apiClient<Transaction>(`/transactions/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

// ─── Auth API ───

export async function authenticateTelegram(
  initData: string
): Promise<AuthResponse> {
  return apiClient<AuthResponse>('/auth/telegram', {
    method: 'POST',
    body: JSON.stringify({ initData: initData }),
  });
}

// ─── Order API ───

export async function createOrder(payload: CreateOrderPayload): Promise<Order> {
  return apiClient<Order>('/orders', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getOrder(id: string): Promise<Order> {
  return apiClient<Order>(`/orders/${id}`);
}

export async function listOrders(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<OrderList> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));
  const query = searchParams.toString();
  return apiClient<OrderList>(`/orders${query ? `?${query}` : ''}`);
}

export async function updateOrderStatus(
  id: string,
  payload: UpdateOrderStatusPayload
): Promise<Order> {
  return apiClient<Order>(`/orders/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

// ─── Conversation API ───

export async function listConversations(params?: {
  limit?: number;
  offset?: number;
}): Promise<ConversationList> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));
  const query = searchParams.toString();
  return apiClient<ConversationList>(`/conversations${query ? `?${query}` : ''}`);
}

export async function getConversation(id: string): Promise<Conversation & { messages: Message[] }> {
  return apiClient<Conversation & { messages: Message[] }>(`/conversations/${id}`);
}

export async function sendOwnerMessage(
  conversationId: string,
  text: string
): Promise<Message> {
  return apiClient<Message>(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}
