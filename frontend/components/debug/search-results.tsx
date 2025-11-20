import { SearchResultCard } from "./search-result-card";
import { Badge } from "@/components/ui/badge";
import type { SearchResponse } from "@/lib/types/search";
import { Loader2 } from "lucide-react";

interface SearchResultsProps {
  response: SearchResponse | null;
  isLoading: boolean;
}

export function SearchResults({ response, isLoading }: SearchResultsProps) {
  // ローディング中
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">検索中...</p>
      </div>
    );
  }

  // 結果なし
  if (!response) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-sm text-muted-foreground">
          検索条件を入力して検索ボタンを押してください
        </p>
      </div>
    );
  }

  // 結果が0件
  if (response.results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-sm text-muted-foreground">
          検索結果が見つかりませんでした
        </p>
      </div>
    );
  }

  // 結果あり
  return (
    <div className="space-y-4">
      {/* ヘッダー */}
      <div className="flex items-center justify-between border-b pb-3">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold">検索結果</h3>
          <Badge variant="secondary">{response.total}件</Badge>
        </div>
        <Badge variant="outline">戦略: {response.strategy}</Badge>
      </div>

      {/* 結果リスト */}
      <div className="space-y-4">
        {response.results.map((result, index) => (
          <SearchResultCard
            key={result.chunk_id}
            result={result}
            rank={index + 1}
          />
        ))}
      </div>
    </div>
  );
}

