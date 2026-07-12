import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspace";
import type { Workspace } from "@/lib/types";

const EMPTY_WORKSPACES: Workspace[] = [];

export function useWorkspaces() {
  const { currentWorkspaceId, setCurrentWorkspaceId } = useWorkspaceStore();

  const { data: workspaces = EMPTY_WORKSPACES, isLoading } = useQuery<Workspace[]>({
    queryKey: ["workspaces"],
    queryFn: () => api.get("/workspaces").then((r) => r.data),
  });

  useEffect(() => {
    if (!isLoading && workspaces.length > 0) {
      const stillValid = workspaces.some((w) => w.id === currentWorkspaceId);
      if (!currentWorkspaceId || !stillValid) {
        setCurrentWorkspaceId(workspaces[0].id);
      }
    }
  }, [isLoading, workspaces, currentWorkspaceId, setCurrentWorkspaceId]);

  const currentWorkspace = workspaces.find((w) => w.id === currentWorkspaceId) ?? null;

  return { workspaces, currentWorkspace, currentWorkspaceId, setCurrentWorkspaceId, isLoading };
}
