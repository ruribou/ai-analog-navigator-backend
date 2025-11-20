"use client";

import { useState } from "react";
import { SearchForm } from "@/components/debug/search-form";
import { SearchResults } from "@/components/debug/search-results";
import { searchAPI, SearchAPIError } from "@/lib/api/search";
import type { SearchRequest, SearchResponse } from "@/lib/types/search";
import { Separator } from "@/components/ui/separator";

export default function SearchDebugPage() {
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (request: SearchRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await searchAPI(request);
      setSearchResponse(response);
    } catch (err) {
      if (err instanceof SearchAPIError) {
        setError(`検索エラー: ${err.message}`);
      } else {
        setError("予期しないエラーが発生しました");
      }
      console.error("Search error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* ヘッダー */}
        <div className="space-y-2 mb-8">
          <h1 className="text-3xl font-bold tracking-tight">
            検索デバッグUI
          </h1>
          <p className="text-muted-foreground">
            Dense / Prefilter+Dense / Hybrid の検索戦略を比較・デバッグするためのインターフェース
          </p>
        </div>

        <Separator className="my-6" />

        {/* メインコンテンツ */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 左カラム: 検索フォーム */}
          <div className="lg:col-span-1">
            <div className="sticky top-8">
              <div className="rounded-lg border bg-card p-6">
                <h2 className="text-xl font-semibold mb-4">検索条件</h2>
                <SearchForm onSearch={handleSearch} isLoading={isLoading} />
              </div>
            </div>
          </div>

          {/* 右カラム: 検索結果 */}
          <div className="lg:col-span-2">
            <div className="rounded-lg border bg-card p-6">
              {/* エラー表示 */}
              {error && (
                <div className="mb-6 p-4 rounded-lg bg-destructive/10 border border-destructive text-destructive text-sm">
                  {error}
                </div>
              )}

              {/* 検索結果 */}
              <SearchResults response={searchResponse} isLoading={isLoading} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

