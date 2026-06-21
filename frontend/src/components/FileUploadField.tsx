import { useId, useRef } from "react";

type Props = {
  label: string;
  accept?: string;
  file: File | null;
  onFileChange: (file: File | null) => void;
  hint?: string;
  disabled?: boolean;
};

export default function FileUploadField({
  label,
  accept = ".xlsx",
  file,
  onFileChange,
  hint,
  disabled,
}: Props) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="space-y-2">
      <span className="block text-sm font-medium text-slate-700">{label}</span>
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
      <input
        id={inputId}
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        disabled={disabled}
        onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
      />
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-medium text-white hover:bg-teal-600 disabled:opacity-50 shadow-sm"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
            />
          </svg>
          Choose file
        </button>
        {file ? (
          <span className="text-sm text-slate-700 bg-slate-100 px-3 py-1.5 rounded-md max-w-md truncate">
            {file.name} ({(file.size / 1024).toFixed(1)} KB)
          </span>
        ) : (
          <span className="text-sm text-slate-400">No file selected</span>
        )}
        {file && (
          <button
            type="button"
            className="text-sm text-red-600 hover:underline"
            onClick={() => {
              onFileChange(null);
              if (inputRef.current) inputRef.current.value = "";
            }}
          >
            Remove
          </button>
        )}
      </div>
    </div>
  );
}
