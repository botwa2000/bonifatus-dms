'use client'

import { useState, useCallback } from 'react'
import DefaultEditor, { BtnBold, BtnItalic, BtnUnderline, BtnLink, BtnStyles, Separator, Toolbar } from 'react-simple-wysiwyg'

interface EmailHtmlEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

const TEMPLATE_VARIABLES = [
  { label: 'User Name', value: '{{user_name}}' },
  { label: 'User Email', value: '{{user_email}}' },
  { label: 'Tier Name', value: '{{tier_name}}' },
  { label: 'App URL', value: '{{app_url}}' },
]

export default function EmailHtmlEditor({ value, onChange, placeholder }: EmailHtmlEditorProps) {
  const [showSource, setShowSource] = useState(false)

  const handleInsertVariable = useCallback((variable: string) => {
    if (showSource) {
      onChange(value + variable)
    } else {
      document.execCommand('insertText', false, variable)
    }
  }, [showSource, value, onChange])

  const handleInsertButton = useCallback(() => {
    const url = prompt('Button URL:', 'https://bonidoc.com/documents/upload')
    if (!url) return
    const text = prompt('Button text:', 'Get Started')
    if (!text) return

    const buttonHtml = `<a href="${url}" style="display:inline-block;padding:12px 24px;background-color:#2563eb;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:600;font-size:16px;">${text}</a>`

    if (showSource) {
      onChange(value + buttonHtml)
    } else {
      document.execCommand('insertHTML', false, buttonHtml)
    }
  }, [showSource, value, onChange])

  if (showSource) {
    return (
      <div>
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <ToolbarButtons
            onInsertVariable={handleInsertVariable}
            onInsertButton={handleInsertButton}
          />
          <button
            type="button"
            onClick={() => setShowSource(false)}
            className="px-3 py-1.5 text-xs font-medium rounded bg-admin-primary text-white hover:opacity-90"
          >
            Visual
          </button>
        </div>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={15}
          placeholder={placeholder}
          className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-gray-900 dark:text-neutral-100 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
        />
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <ToolbarButtons
          onInsertVariable={handleInsertVariable}
          onInsertButton={handleInsertButton}
        />
        <button
          type="button"
          onClick={() => setShowSource(true)}
          className="px-3 py-1.5 text-xs font-medium rounded bg-gray-200 dark:bg-neutral-600 text-gray-700 dark:text-neutral-200 hover:bg-gray-300 dark:hover:bg-neutral-500"
        >
          Source
        </button>
      </div>
      <div className="border border-gray-300 dark:border-neutral-600 rounded-md overflow-hidden [&_.rsw-editor]:min-h-[300px] [&_.rsw-editor]:bg-white [&_.rsw-editor]:dark:bg-neutral-700 [&_.rsw-editor]:text-gray-900 [&_.rsw-editor]:dark:text-neutral-100 [&_.rsw-ce]:min-h-[300px] [&_.rsw-ce]:p-3">
        <DefaultEditor
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        >
          <Toolbar>
            <BtnBold />
            <BtnItalic />
            <BtnUnderline />
            <Separator />
            <BtnLink />
            <BtnStyles />
          </Toolbar>
        </DefaultEditor>
      </div>
    </div>
  )
}

function ToolbarButtons({
  onInsertVariable,
  onInsertButton,
}: {
  onInsertVariable: (v: string) => void
  onInsertButton: () => void
}) {
  return (
    <>
      <select
        onChange={(e) => {
          if (e.target.value) {
            onInsertVariable(e.target.value)
            e.target.value = ''
          }
        }}
        className="px-2 py-1.5 text-xs border border-gray-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-700 text-gray-700 dark:text-neutral-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
        defaultValue=""
      >
        <option value="" disabled>Insert Variable...</option>
        {TEMPLATE_VARIABLES.map((v) => (
          <option key={v.value} value={v.value}>{v.label} — {v.value}</option>
        ))}
      </select>
      <button
        type="button"
        onClick={onInsertButton}
        className="px-3 py-1.5 text-xs font-medium rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50"
      >
        Insert Button
      </button>
    </>
  )
}
