import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SearchResultItem } from "@/lib/types/search";
import { ExternalLink } from "lucide-react";

interface SearchResultCardProps {
  result: SearchResultItem;
  rank: number;
}

export function SearchResultCard({ result, rank }: SearchResultCardProps) {
  return (
    <Card className="hover:bg-accent/50 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono">
              #{rank}
            </Badge>
            <Badge variant="secondary" className="font-mono">
              Score: {result.score.toFixed(3)}
            </Badge>
          </div>
          <Badge variant="outline" className="text-xs">
            {result.chunk_id}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* チャンクテキスト */}
        <div className="text-sm leading-relaxed line-clamp-3">
          {result.text}
        </div>

        {/* メタデータ */}
        <div className="flex flex-wrap gap-2">
          {result.metadata.campus && (
            <Badge variant="outline" className="text-xs">
              🏫 {result.metadata.campus}
            </Badge>
          )}
          {result.metadata.department && (
            <Badge variant="outline" className="text-xs">
              🎓 {result.metadata.department}
            </Badge>
          )}
          {result.metadata.lab && (
            <Badge variant="outline" className="text-xs">
              🔬 {result.metadata.lab}
            </Badge>
          )}
          {result.metadata.professor && result.metadata.professor.length > 0 && (
            <Badge variant="outline" className="text-xs">
              👨‍🏫 {result.metadata.professor.join(", ")}
            </Badge>
          )}
          {result.metadata.tags && result.metadata.tags.length > 0 && (
            result.metadata.tags.map((tag, idx) => (
              <Badge key={idx} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))
          )}
        </div>

        {/* ソースURL */}
        {result.source_url && (
          <a
            href={result.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-primary hover:underline"
          >
            <ExternalLink className="h-3 w-3" />
            ソースを表示
          </a>
        )}
      </CardContent>
    </Card>
  );
}

