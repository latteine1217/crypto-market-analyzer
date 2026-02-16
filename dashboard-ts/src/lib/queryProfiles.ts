export const QUERY_PROFILES = {
  ultra: {
    refetchInterval: 1000,
  },
  high: {
    refetchInterval: 5000,
  },
  medium: {
    refetchInterval: 10000,
  },
  low: {
    refetchInterval: 60000,
  },
  slow: {
    refetchInterval: 300000,
  },
  tenMinutes: {
    refetchInterval: 600000,
  },
  hourly: {
    refetchInterval: 3600000,
  },
  static: {
    refetchInterval: false,
  },
} as const;

export const QUERY_DEFAULTS = {
  staleTime: 30 * 1000,
  gcTime: 2 * 60 * 1000,
  refetchInterval: false,
  refetchOnWindowFocus: true,
  retry: 1,
} as const;
