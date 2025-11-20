import type { SearchRequest, SearchResponse } from "@/lib/types/search";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class SearchAPIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: unknown
  ) {
    super(message);
    this.name = "SearchAPIError";
  }
}

export async function searchAPI(
  request: SearchRequest
): Promise<SearchResponse> {
  try {
    console.log('API_BASE_URL:', API_BASE_URL);
    console.log('Request:', request);
    
    const response = await fetch(`${API_BASE_URL}/api/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new SearchAPIError(
        errorData.detail || "検索リクエストに失敗しました",
        response.status,
        errorData
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof SearchAPIError) {
      throw error;
    }
    console.error('Network error details:', error);
    throw new SearchAPIError(
      `ネットワークエラーが発生しました (API URL: ${API_BASE_URL})`,
      undefined,
      error
    );
  }
}

