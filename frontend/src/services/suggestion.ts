import axios from 'axios';
import type {
  CommandSuggestion,
  SuggestionResponse,
  FeedbackRequest,
  HistoryEntry,
  UserProfile,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

const localCache = new Map<string, { data: CommandSuggestion[]; ts: number }>();
const CACHE_TTL = 30000;

function getCached(key: string): CommandSuggestion[] | null {
  const entry = localCache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.ts > CACHE_TTL) {
    localCache.delete(key);
    return null;
  }
  return entry.data;
}

function setCache(key: string, data: CommandSuggestion[]) {
  localCache.set(key, { data, ts: Date.now() });
  if (localCache.size > 200) {
    const oldest = Array.from(localCache.entries()).sort((a, b) => a[1].ts - b[1].ts);
    for (let i = 0; i < 50; i++) {
      localCache.delete(oldest[i][0]);
    }
  }
}

export const suggestionApi = {
  getSuggestions: async (prefix: string, limit = 20): Promise<SuggestionResponse> => {
    const cacheKey = `prefix:${prefix}:${limit}`;
    const cached = getCached(cacheKey);
    if (cached) {
      return { suggestions: cached, total: cached.length, elapsed_ms: 0.5 };
    }
    const resp = await api.get('/suggestions', { params: { prefix, limit } });
    setCache(cacheKey, resp.data.suggestions);
    return resp.data;
  },

  nlpQuery: async (query: string): Promise<SuggestionResponse> => {
    const resp = await api.post('/suggestions/nlp', { query });
    return resp.data;
  },

  submitFeedback: async (data: FeedbackRequest): Promise<void> => {
    await api.post('/suggestions/feedback', data);
    for (const key of localCache.keys()) {
      if (key.startsWith('prefix:')) {
        localCache.delete(key);
      }
    }
  },

  getCollaborative: async (limit = 10): Promise<SuggestionResponse> => {
    const resp = await api.get('/suggestions/collaborative', { params: { limit } });
    return resp.data;
  },

  getHistory: async (limit = 50, category?: string): Promise<HistoryEntry[]> => {
    const resp = await api.get('/suggestions/history', { params: { limit, category } });
    return resp.data;
  },

  getProfile: async (): Promise<UserProfile> => {
    const resp = await api.get('/suggestions/profile');
    return resp.data;
  },
};

export default suggestionApi;
