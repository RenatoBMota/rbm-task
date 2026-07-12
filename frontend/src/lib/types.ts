export type TaskPriority = "P1" | "P2" | "P3" | "P4";
export type TaskStatus = "todo" | "in_progress" | "in_review" | "done" | "cancelled";

export type TaskRecurrence = "none" | "daily" | "weekly" | "monthly";

export interface Label {
  id: number;
  name: string;
  color: string;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  due_date: string | null;
  start_date: string | null;
  is_milestone: boolean;
  estimated_minutes: number | null;
  is_completed: boolean;
  completed_at: string | null;
  position: number;
  project_id: number | null;
  assignee_id: number | null;
  parent_id: number | null;
  recurrence: TaskRecurrence;
  location: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  subtask_count: number;
  labels: Label[];
}

export type DependencyType = "finish_start" | "start_start" | "finish_finish" | "start_finish";
export type DependencyHardness = "strong" | "rubber";

export interface GanttDependency {
  id: number;
  task_id: number;
  depends_on_id: number;
  dependency_type: DependencyType;
  lag_days: number;
  hardness: DependencyHardness;
}

export interface GanttData {
  tasks: Task[];
  dependencies: GanttDependency[];
  critical_task_ids: number[];
  task_costs: Record<string, number>;
}

export interface Resource {
  id: number;
  name: string;
  role: string | null;
  email: string | null;
  standard_rate: number;
  workspace_id: number;
}

export interface ResourceAssignment {
  id: number;
  task_id: number;
  resource_id: number;
  resource_name: string;
  standard_rate: number;
  allocation_percent: number;
  is_coordinator: boolean;
}

export interface ResourceUtilization {
  resource_id: number;
  resource_name: string;
  total_allocation_percent: number;
  task_count: number;
}

export interface GanttBaselineTaskData {
  task_id: number | null;
  title: string;
  start_date: string | null;
  due_date: string | null;
}

export interface GanttBaselineSummary {
  id: number;
  project_id: number;
  name: string;
  created_at: string;
}

export interface GanttBaseline extends GanttBaselineSummary {
  tasks: GanttBaselineTaskData[];
}

export interface StatusBreakdownItem {
  status: TaskStatus;
  count: number;
}

export interface ExecutiveReportTeamMember {
  user_id: number;
  full_name: string;
  active_task_count: number;
  completed_task_count: number;
}

export interface ExecutiveReport {
  project_id: number;
  project_name: string;
  start_date: string;
  end_date: string;
  generated_at: string;
  total_tasks: number;
  completed_tasks: number;
  progress_percent: number;
  expected_progress_percent: number;
  on_schedule: boolean;
  overdue_tasks: number;
  critical_task_count: number;
  total_cost: number;
  risk_score: number;
  risk_level: "low" | "medium" | "high";
  status_breakdown: StatusBreakdownItem[];
  team: ExecutiveReportTeamMember[];
}

export type RecapPeriod = "daily" | "weekly" | "monthly" | "custom";

export interface RecapContributor {
  user_id: number;
  full_name: string;
  completed_count: number;
}

export interface Recap {
  period: RecapPeriod;
  period_start: string;
  period_end: string;
  tasks_created: number;
  tasks_completed: number;
  tasks_overdue: number;
  previous_tasks_completed: number;
  completed_delta: number;
  top_contributors: RecapContributor[];
}

export type IndicatorType = "quantity" | "value" | "percentage" | "decimal" | "integer";
export type KRCadence = "weekly" | "biweekly" | "monthly";
export type KRDirection = "increase" | "decrease";
export type TrendDirection = "up" | "down" | "flat";
export type TrendLabel = "positive" | "negative" | "stable";

export interface Objective {
  id: number;
  workspace_id: number;
  title: string;
  description: string | null;
  start_date: string;
  end_date: string;
  owner_id: number | null;
  created_at: string;
}

export interface KeyResultSummary {
  id: number;
  code: string;
  title: string;
  indicator_type: IndicatorType;
  direction: KRDirection;
  current_value: number | null;
  target_value: number;
  progress_percent: number;
  trend_direction: TrendDirection;
}

export interface ObjectiveDetail {
  id: number;
  title: string;
  description: string | null;
  start_date: string;
  end_date: string;
  owner_id: number | null;
  performance_percent: number;
  key_results: KeyResultSummary[];
}

export interface KeyResult {
  id: number;
  objective_id: number;
  code: string;
  title: string;
  indicator_type: IndicatorType;
  direction: KRDirection;
  cadence: KRCadence;
  baseline_value: number;
  target_value: number;
  owner_id: number | null;
  created_at: string;
}

export interface KRHistoryPoint {
  period_label: string;
  value: number;
  target: number;
}

export interface InitiativeSummary {
  id: number;
  title: string;
  weight_percent: number;
  progress_percent: number;
  contribution_percent: number;
  is_completed: boolean;
  task_count: number;
}

export interface KeyResultDetail {
  id: number;
  objective_id: number;
  code: string;
  title: string;
  indicator_type: IndicatorType;
  direction: KRDirection;
  cadence: KRCadence;
  baseline_value: number;
  target_value: number;
  owner_id: number | null;
  current_value: number | null;
  previous_value: number | null;
  variation_abs: number | null;
  variation_pct: number | null;
  average_to_date: number | null;
  best_value: number | null;
  worst_value: number | null;
  gap_to_target: number | null;
  progress_percent: number;
  trend_direction: TrendDirection;
  trend_label: TrendLabel;
  forecast_value: number | null;
  forecast_hits_target: boolean | null;
  score: number;
  history: KRHistoryPoint[];
  initiatives: InitiativeSummary[];
  initiatives_rollup_percent: number;
}

export interface Initiative {
  id: number;
  key_result_id: number;
  title: string;
  weight_percent: number;
  owner_id: number | null;
  is_completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface OkrActionDetail {
  id: number;
  title: string;
  weight_percent: number;
  owner_id: number | null;
  due_date: string | null;
  is_completed: boolean;
  progress_percent: number;
}

export interface OkrTaskDetail {
  id: number;
  title: string;
  weight_percent: number;
  owner_id: number | null;
  due_date: string | null;
  is_completed: boolean;
  progress_percent: number;
  actions: OkrActionDetail[];
}

export interface InitiativeDetail {
  id: number;
  key_result_id: number;
  title: string;
  weight_percent: number;
  owner_id: number | null;
  is_completed: boolean;
  progress_percent: number;
  tasks: OkrTaskDetail[];
}

export interface OkrTask {
  id: number;
  initiative_id: number;
  title: string;
  weight_percent: number;
  owner_id: number | null;
  due_date: string | null;
  is_completed: boolean;
  updated_at: string;
}

export interface OkrAction {
  id: number;
  task_id: number;
  title: string;
  weight_percent: number;
  owner_id: number | null;
  due_date: string | null;
  is_completed: boolean;
  updated_at: string;
}

export interface OkrExecutiveSummary {
  objectives_count: number;
  key_results_count: number;
  initiatives_count: number;
  tasks_count: number;
  actions_count: number;
  overall_performance_percent: number;
  expected_performance_percent: number;
  overdue_count: number;
  on_time_percent: number;
  completed_percent: number;
}

export interface OkrAlert {
  level: "warning" | "critical";
  entity_type: string;
  entity_id: number;
  entity_title: string;
  message: string;
}

export const INDICATOR_TYPE_LABELS: Record<IndicatorType, string> = {
  quantity: "Quantidade",
  value: "Valor",
  percentage: "Percentual",
  decimal: "Decimal",
  integer: "Inteiro",
};

export const KR_CADENCE_LABELS: Record<KRCadence, string> = {
  weekly: "Semanal",
  biweekly: "Quinzenal",
  monthly: "Mensal",
};

export interface Project {
  id: number;
  name: string;
  description: string | null;
  start_date: string;
  end_date: string;
  color: string;
  icon: string;
  is_archived: boolean;
  is_template: boolean;
  workspace_id: number | null;
}

export type WorkspaceRole = "owner" | "admin" | "member";

export interface Workspace {
  id: number;
  name: string;
  color: string;
  icon: string;
  owner_id: number;
  created_at: string;
  my_role: WorkspaceRole;
}

export interface WorkspaceMember {
  id: number;
  user_id: number;
  email: string;
  full_name: string;
  role: WorkspaceRole;
}

export interface Reminder {
  id: number;
  task_id: number;
  remind_at: string;
  is_sent: boolean;
}

export interface ChecklistItem {
  id: number;
  title: string;
  is_completed: boolean;
  position: number;
  task_id: number;
}

export interface Comment {
  id: number;
  content: string;
  task_id: number;
  author_id: number;
  created_at: string;
}

export interface Attachment {
  id: number;
  filename: string;
  content_type: string | null;
  size_bytes: number | null;
  task_id: number;
  uploaded_by_id: number;
  created_at: string;
}

export type NotificationType = "task_assigned" | "comment_mention" | "new_comment";

export interface Notification {
  id: number;
  type: NotificationType;
  message: string;
  is_read: boolean;
  task_id: number | null;
  created_at: string;
}

export const TASK_STATUSES: { value: TaskStatus; label: string }[] = [
  { value: "todo", label: "A Fazer" },
  { value: "in_progress", label: "Em Progresso" },
  { value: "in_review", label: "Em Revisão" },
  { value: "done", label: "Concluído" },
  { value: "cancelled", label: "Cancelado" },
];

export const PRIORITY_COLORS: Record<TaskPriority, string> = {
  P1: "bg-red-100 text-red-700 border-red-200",
  P2: "bg-orange-100 text-orange-700 border-orange-200",
  P3: "bg-blue-100 text-blue-700 border-blue-200",
  P4: "bg-slate-100 text-slate-600 dark:text-slate-400 border-slate-200",
};

export const DEPENDENCY_TYPE_LABELS: Record<DependencyType, string> = {
  finish_start: "Término → Início",
  start_start: "Início → Início",
  finish_finish: "Término → Término",
  start_finish: "Início → Término",
};

export const DEPENDENCY_TYPE_SHORT: Record<DependencyType, string> = {
  finish_start: "FS",
  start_start: "SS",
  finish_finish: "FF",
  start_finish: "SF",
};
