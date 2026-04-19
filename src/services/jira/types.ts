export interface JiraSearchResponse {
  issues: JiraIssue[];
  isLast?: boolean;
  nextPageToken?: string;
}

export interface JiraIssue {
  id: string;
  key: string;
  fields: Record<string, unknown>;
  changelog?: {
    histories?: JiraHistory[];
  };
}

export interface JiraHistory {
  created: string;
  items: JiraHistoryItem[];
}

export interface JiraHistoryItem {
  field: string;
  fieldtype?: string;
  fromString?: string | null;
  toString?: string | null;
}
