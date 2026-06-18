export interface ServerConfig {
  id: string;
  name: string;
  host: string;
  port: number;
  username: string;
  password: string;
  private_key: string;
  tags: string[];
}

export interface ExecutionResult {
  task_id: string;
  server_id: string;
  server_name: string;
  command: string;
  exit_code: number | null;
  stdout: string;
  stderr: string;
  start_time: string;
  end_time: string | null;
  status: 'pending' | 'running' | 'success' | 'failed' | 'error';
}

export interface StreamMessage {
  type: 'output' | 'status';
  task_id: string;
  server_id: string;
  server_name: string;
  stream: 'stdout' | 'stderr' | '';
  content: string;
  exit_code: number | null;
  status: string;
  timestamp: string;
}

export interface ScriptTemplate {
  id: string;
  name: string;
  description: string;
  script_content: string;
  interpreter: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface LogEntry {
  task_id: string;
  server_name: string;
  server_id: string;
  command: string;
  script_name: string | null;
  start_time: string;
  end_time: string;
  status: string;
  exit_code: number | null;
  output: string;
  log_file: string;
}

export interface CommandExecuteRequest {
  server_ids: string[];
  command: string;
  timeout?: number;
  env?: Record<string, string>;
}

export interface ScriptExecuteRequest {
  server_ids: string[];
  script_content: string;
  script_name?: string;
  interpreter?: string;
  args?: string[];
  timeout?: number;
}

export interface CommandSuggestion {
  command: string;
  category: string;
  score: number;
  frequency: number;
  is_history: boolean;
  source: string;
}

export interface SuggestionResponse {
  suggestions: CommandSuggestion[];
  total: number;
  elapsed_ms: number;
}

export interface FeedbackRequest {
  command: string;
  useful: boolean;
  reason?: string;
}

export interface HistoryEntry {
  command: string;
  timestamp: string;
  category: string;
  exit_code: number;
  count: number;
}

export interface UserProfile {
  category_weights: Record<string, number>;
  top_categories: [string, number][];
  total_commands: number;
  total_feedback: number;
  negative_commands_count: number;
}
