"use client";

import React from "react";

const LANGUAGES = [
  { code: "en", label: "English (default)" },
  { code: "ru", label: "Russian" },
  { code: "es", label: "Spanish" },
  { code: "de", label: "German" },
  { code: "fr", label: "French" },
];

export default function LanguageSelector({ value, onChange }: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1 mt-4">
      <label className="text-sm font-medium text-gray-700">Plan language</label>
      <select
        className="border rounded-md px-3 py-2 bg-white"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label}
          </option>
        ))}
      </select>
    </div>
  );
}
