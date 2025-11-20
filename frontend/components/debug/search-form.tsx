"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { SearchFilters } from "./search-filters";
import type { SearchRequest, SearchStrategy, SearchFilters as SearchFiltersType } from "@/lib/types/search";
import { Search } from "lucide-react";

interface SearchFormProps {
  onSearch: (request: SearchRequest) => void;
  isLoading: boolean;
}

export function SearchForm({ onSearch, isLoading }: SearchFormProps) {
  const [query, setQuery] = useState("");
  const [strategy, setStrategy] = useState<SearchStrategy>("dense");
  const [topK, setTopK] = useState(10);
  const [alpha, setAlpha] = useState(0.6);
  const [beta, setBeta] = useState(0.4);
  const [filters, setFilters] = useState<SearchFiltersType>({});
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // バリデーション
    if (!query.trim()) {
      setError("検索クエリを入力してください");
      return;
    }

    if (topK < 1 || topK > 50) {
      setError("top_k は 1〜50 の範囲で指定してください");
      return;
    }

    if (strategy === "hybrid") {
      if (alpha < 0 || alpha > 1) {
        setError("alpha は 0.0〜1.0 の範囲で指定してください");
        return;
      }
      if (beta < 0 || beta > 1) {
        setError("beta は 0.0〜1.0 の範囲で指定してください");
        return;
      }
    }

    // 空のフィルタを除外
    const cleanedFilters: SearchFiltersType = {};
    Object.entries(filters).forEach(([key, value]) => {
      if (value && value.trim() !== "") {
        cleanedFilters[key] = value;
      }
    });

    const request: SearchRequest = {
      query: query.trim(),
      strategy,
      top_k: topK,
    };

    // 戦略に応じてパラメータを追加
    if (strategy === "prefilter_dense" || strategy === "hybrid") {
      if (Object.keys(cleanedFilters).length > 0) {
        request.filters = cleanedFilters;
      }
    }

    if (strategy === "hybrid") {
      request.alpha = alpha;
      request.beta = beta;
    }

    onSearch(request);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* クエリ入力 */}
      <div className="space-y-2">
        <Label htmlFor="query">検索クエリ *</Label>
        <Input
          id="query"
          placeholder="例: 神戸先生の研究内容を教えて"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
      </div>

      <Separator />

      {/* 検索戦略選択 */}
      <div className="space-y-3">
        <Label>検索戦略 *</Label>
        <Tabs value={strategy} onValueChange={(v) => setStrategy(v as SearchStrategy)}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="dense">Dense</TabsTrigger>
            <TabsTrigger value="prefilter_dense">Prefilter+Dense</TabsTrigger>
            <TabsTrigger value="hybrid">Hybrid</TabsTrigger>
          </TabsList>

          <TabsContent value="dense" className="space-y-4 mt-4">
            <p className="text-sm text-muted-foreground">
              ベクトル検索のみを使用します（意味検索）
            </p>
          </TabsContent>

          <TabsContent value="prefilter_dense" className="space-y-4 mt-4">
            <p className="text-sm text-muted-foreground">
              メタデータフィルタを適用してからベクトル検索を行います
            </p>
          </TabsContent>

          <TabsContent value="hybrid" className="space-y-4 mt-4">
            <p className="text-sm text-muted-foreground">
              Dense（ベクトル検索）とBM25（キーワード検索）のスコアを合成します
            </p>
          </TabsContent>
        </Tabs>
      </div>

      <Separator />

      {/* パラメータ */}
      <div className="space-y-4">
        <Label>パラメータ</Label>
        
        <div className="space-y-2">
          <Label htmlFor="top_k" className="text-sm">
            取得件数 (top_k): {topK}
          </Label>
          <Input
            id="top_k"
            type="number"
            min={1}
            max={50}
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value) || 10)}
            disabled={isLoading}
          />
        </div>

        {strategy === "hybrid" && (
          <>
            <div className="space-y-2">
              <Label htmlFor="alpha" className="text-sm">
                Dense検索の重み (alpha): {alpha.toFixed(2)}
              </Label>
              <Input
                id="alpha"
                type="number"
                step="0.1"
                min={0}
                max={1}
                value={alpha}
                onChange={(e) => setAlpha(parseFloat(e.target.value) || 0.6)}
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="beta" className="text-sm">
                BM25検索の重み (beta): {beta.toFixed(2)}
              </Label>
              <Input
                id="beta"
                type="number"
                step="0.1"
                min={0}
                max={1}
                value={beta}
                onChange={(e) => setBeta(parseFloat(e.target.value) || 0.4)}
                disabled={isLoading}
              />
            </div>
          </>
        )}
      </div>

      {/* フィルタ（Prefilter+DenseまたはHybridの場合のみ表示） */}
      {(strategy === "prefilter_dense" || strategy === "hybrid") && (
        <>
          <Separator />
          <div className="space-y-3">
            <Label>メタデータフィルタ（オプション）</Label>
            <SearchFilters filters={filters} onChange={setFilters} />
          </div>
        </>
      )}

      {/* エラー表示 */}
      {error && (
        <div className="text-sm text-destructive">
          {error}
        </div>
      )}

      {/* 検索ボタン */}
      <Button type="submit" className="w-full" disabled={isLoading}>
        <Search className="mr-2 h-4 w-4" />
        {isLoading ? "検索中..." : "検索"}
      </Button>
    </form>
  );
}

