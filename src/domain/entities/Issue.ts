export interface Issue {
  id: string;
  type: "task" | "bug" | "story";
  status: string;
  createdAt: string;
  startedAt: string | null;
  resolvedAt: string | null;
  assignee: string | null;
  estimate: number | null;
  storyPoints: number | null;
  reopened: boolean;
}
