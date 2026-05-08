interface StatusBarProps {
  loading: boolean;
  error: string | null;
  queryEcho: string | null;
}

export function StatusBar({ loading, error, queryEcho }: StatusBarProps) {
  if (loading) {
    return (
      <div className="mt-4 text-stone-700" aria-live="polite">
        Retrieving and synthesizing
        <span className="inline-block w-6 ml-0.5 animate-pulse">...</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="mt-4 text-red-800" role="alert">
        {error}
      </div>
    );
  }
  if (queryEcho) {
    return (
      <div className="mt-4 text-stone-600 text-sm">
        Query: {queryEcho}
      </div>
    );
  }
  return null;
}
