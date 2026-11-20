import type { Ref } from "react";
import { Sparkles } from "lucide-react";

export function DraftEmailEditor({
  headingId,
  headingRef,
  inputId,
  value,
  onChange,
  disabled,
  placeholder,
  description,
  maxLength,
  showEditor = true,
}: {
  headingId: string;
  headingRef?: Ref<HTMLHeadingElement>;
  inputId: string;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
  placeholder: string;
  description?: string;
  maxLength?: number;
  showEditor?: boolean;
}) {
  return (
    <>
      <div className="live-draft-heading">
        <h2
          id={headingId}
          ref={headingRef}
          tabIndex={headingRef ? -1 : undefined}
        >
          Draft email
        </h2>
        <span className="live-ai-badge">
          <Sparkles size={14} aria-hidden="true" /> AI-assisted drafting
        </span>
      </div>
      {description && <p className="live-draft-description">{description}</p>}
      {showEditor && (
        <label className="editor-label live-draft-editor" htmlFor={inputId}>
          Response
          <textarea
            id={inputId}
            rows={10}
            value={value}
            placeholder={placeholder}
            disabled={disabled}
            maxLength={maxLength}
            onChange={(event) => onChange(event.target.value)}
          />
        </label>
      )}
    </>
  );
}
