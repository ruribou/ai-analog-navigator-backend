import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { SearchFilters } from "@/lib/types/search";

interface SearchFiltersProps {
  filters: SearchFilters;
  onChange: (filters: SearchFilters) => void;
}

export function SearchFilters({ filters, onChange }: SearchFiltersProps) {
  const handleFilterChange = (key: string, value: string) => {
    const newFilters = { ...filters };
    if (value.trim() === "") {
      delete newFilters[key];
    } else {
      newFilters[key] = value;
    }
    onChange(newFilters);
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="filter-department">学部・研究科</Label>
        <Input
          id="filter-department"
          placeholder="例: 理工学部"
          value={filters.department || ""}
          onChange={(e) => handleFilterChange("department", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="filter-professor">教員名</Label>
        <Input
          id="filter-professor"
          placeholder="例: 神戸 英利"
          value={filters.professor || ""}
          onChange={(e) => handleFilterChange("professor", e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="filter-campus">キャンパス</Label>
          <Input
            id="filter-campus"
            placeholder="例: hatoyama"
            value={filters.campus || ""}
            onChange={(e) => handleFilterChange("campus", e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="filter-lab">研究室</Label>
          <Input
            id="filter-lab"
            placeholder="例: KAM Lab"
            value={filters.lab || ""}
            onChange={(e) => handleFilterChange("lab", e.target.value)}
          />
        </div>
      </div>
    </div>
  );
}

