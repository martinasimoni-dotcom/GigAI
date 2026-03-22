export default function EmptyState() {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-20 px-6 animate-fade-in">
      {/* Illustration */}
      <div className="relative mb-6">
        <div className="w-24 h-24 bg-brand-50 rounded-3xl flex items-center justify-center">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <rect x="6" y="14" width="36" height="26" rx="4" fill="#DBEAFE" />
            <rect x="6" y="14" width="36" height="26" rx="4" stroke="#3B82F6" strokeWidth="2" />
            <path d="M14 14V10a2 2 0 012-2h16a2 2 0 012 2v4" stroke="#3B82F6" strokeWidth="2" />
            <circle cx="24" cy="27" r="5" fill="#3B82F6" opacity=".25" />
            <circle cx="24" cy="27" r="3" fill="#3B82F6" />
            <path d="M24 24v3l2 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
        {/* Decorative dots */}
        <div className="absolute -top-1 -right-1 w-4 h-4 bg-success-100 rounded-full" />
        <div className="absolute -bottom-1 -left-2 w-3 h-3 bg-warning-100 rounded-full" />
      </div>

      <h3 className="text-lg font-bold text-gray-900 mb-1">No proposals yet</h3>
      <p className="text-sm text-gray-500 text-center max-w-xs leading-relaxed">
        Use the <span className="font-medium text-brand-600">Process RFI</span> panel above to generate a proposal from an ACC RFI.
      </p>
    </div>
  )
}
