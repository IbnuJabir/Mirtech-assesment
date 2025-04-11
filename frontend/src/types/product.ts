export interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  category: string;
  stock_quantity: number;
  created_at: string;
  updated_at: string;
}

export interface PaginatedProducts {
  data: Product[];
  total_count: number;
  page: number;
  limit: number;
}

export interface ProductQueryParams {
  page: number;
  limit: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  category?: string;
  search?: string;
}
