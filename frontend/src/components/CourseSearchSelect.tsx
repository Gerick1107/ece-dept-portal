import { useEffect, useId, useMemo, useRef, useState } from "react";

type Props = {
  courses: string[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  className?: string;
  emptyMessage?: string;
};

export default function CourseSearchSelect({
  courses,
  value,
  onChange,
  placeholder = "Type to search courses…",
  required = false,
  className = "w-full border rounded-lg px-3 py-2",
  emptyMessage = "No matching courses",
}: Props) {
  const listId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setQuery(value);
  }, [value]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return courses;
    return courses.filter((c) => c.toLowerCase().includes(q));
  }, [courses, query]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  function pick(course: string) {
    onChange(course);
    setQuery(course);
    setOpen(false);
  }

  return (
    <div ref={rootRef} className="relative">
      <input
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        value={query}
        onChange={(e) => {
          const next = e.target.value;
          setQuery(next);
          setOpen(true);
          if (courses.includes(next)) {
            onChange(next);
          } else if (!next.trim()) {
            onChange("");
          }
        }}
        onFocus={() => setOpen(true)}
        placeholder={courses.length ? placeholder : "Loading courses…"}
        required={required && !value}
        className={className}
        autoComplete="off"
      />
      {open && courses.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border bg-white shadow-lg text-sm"
        >
          {filtered.length === 0 ? (
            <li className="px-3 py-2 text-slate-500">{emptyMessage}</li>
          ) : (
            filtered.map((course) => (
              <li key={course}>
                <button
                  type="button"
                  role="option"
                  aria-selected={course === value}
                  className={`w-full px-3 py-2 text-left hover:bg-teal-50 ${
                    course === value ? "bg-teal-50 font-medium" : ""
                  }`}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => pick(course)}
                >
                  {course}
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
