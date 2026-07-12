import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Label } from "@/lib/types";

const EMPTY_LABELS: Label[] = [];

export function useLabels() {
  const qc = useQueryClient();

  const { data: labels = EMPTY_LABELS, isLoading } = useQuery<Label[]>({
    queryKey: ["labels"],
    queryFn: () => api.get("/labels").then((r) => r.data),
  });

  const createLabel = useMutation({
    mutationFn: (data: { name: string; color?: string }) =>
      api.post("/labels", data).then((r) => r.data as Label),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["labels"] }),
  });

  const updateLabel = useMutation({
    mutationFn: ({ id, ...data }: { id: number; name?: string; color?: string }) =>
      api.put(`/labels/${id}`, data).then((r) => r.data as Label),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["labels"] }),
  });

  const deleteLabel = useMutation({
    mutationFn: (id: number) => api.delete(`/labels/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["labels"] }),
  });

  return { labels, isLoading, createLabel, updateLabel, deleteLabel };
}
