import { useCallback, useState } from "react";
import { apiPostForm } from "../services/api";
import type { MarksParsePreview } from "../types/copo";

/**
 * Auto-parse consolidated marks on upload (legacy portal behaviour).
 * Generator page uses persist=false so no orphan DB row is created before final-submit.
 */
export function useMarksFileParse() {
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState("");

  const parseMarksFile = useCallback(
    async (
      file: File,
      courseTitle?: string,
      options?: { persist?: boolean }
    ): Promise<MarksParsePreview | null> => {
      setParsing(true);
      setError("");
      const fd = new FormData();
      fd.append("course_file", file);
      if (courseTitle?.trim()) fd.append("course_title", courseTitle.trim());
      fd.append("persist", options?.persist === false ? "false" : "true");
      try {
        const r = await apiPostForm<MarksParsePreview>("/copo/parse-students", fd);
        return r;
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Could not parse marks file";
        setError(msg);
        return null;
      } finally {
        setParsing(false);
      }
    },
    []
  );

  return { parseMarksFile, parsing, error, setError };
}
