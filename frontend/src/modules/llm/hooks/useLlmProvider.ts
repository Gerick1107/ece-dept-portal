import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchLlmProviders,
  type LlmProviderId,
  type LlmProviderInfo,
} from "../services/llmInsightsApi";

const STORAGE_KEY = "llm_provider";

function readStored(): LlmProviderId | null {
  const v = localStorage.getItem(STORAGE_KEY);
  return v === "groq" || v === "local" ? v : null;
}

/**
 * Shared state for the per-request LLM provider choice (Cloud Groq vs Local Ollama).
 * The selection persists across the session via localStorage, and provider
 * availability is fetched so the UI can warn before a request is sent.
 */
export function useLlmProvider() {
  const [provider, setProviderState] = useState<LlmProviderId>(() => readStored() ?? "groq");
  const [providers, setProviders] = useState<LlmProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const setProvider = useCallback((next: LlmProviderId) => {
    setProviderState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }, []);

  useEffect(() => {
    let active = true;
    fetchLlmProviders()
      .then((res) => {
        if (!active) return;
        setProviders(res.providers);
        // Adopt the backend default only if the user hasn't chosen before.
        if (!readStored() && res.default) setProviderState(res.default);
      })
      .catch(() => {
        if (active) setProviders([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const currentInfo = useMemo(
    () => providers.find((p) => p.id === provider) ?? null,
    [providers, provider]
  );

  return { provider, setProvider, providers, loading, currentInfo };
}
