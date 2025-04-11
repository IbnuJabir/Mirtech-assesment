import type { ProductQueryParams, PaginatedProducts } from "@/types/product";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchProducts(
  params: ProductQueryParams
): Promise<PaginatedProducts> {
  const queryParams = new URLSearchParams();

  // Add all parameters to query string
  queryParams.append("page", params.page.toString());
  queryParams.append("limit", params.limit.toString());

  if (params.sort_by) {
    queryParams.append("sort_by", params.sort_by);
  }

  if (params.sort_order) {
    queryParams.append("sort_order", params.sort_order);
  }

  if (params.category) {
    queryParams.append("category", params.category);
  }

  if (params.search) {
    queryParams.append("search", params.search);
  }

  const response = await fetch(
    `${BASE_URL}/api/v1/products?${queryParams.toString()}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch products");
  }
  return response.json();
}
