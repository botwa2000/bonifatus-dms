// frontend/src/components/DocumentAnalysisProgress.tsx
'use client'

import { useEffect, useState } from 'react'
import { designTokens } from '@/design/themes/tokens'

interface DocumentAnalysisProgressProps {
  fileCount: number
}

type Phase = 'security' | 'analysis' | 'complete'

const PHASE_DURATIONS = {
  security: 3000,    // 3 seconds for AV scan (estimated)
  analysis: 5000,    // 5 seconds for OCR + classification (estimated)
}

const PHASES = [
  {
    id: 'security' as Phase,
    label: 'Security Scan',
    description: 'Scanning for malware and validating file integrity',
    icon: '🛡️',
    color: designTokens.colors.admin.warning,
  },
  {
    id: 'analysis' as Phase,
    label: 'Document Analysis',
    description: 'Extracting text, detecting language, and classifying content',
    icon: '🔍',
    color: designTokens.colors.admin.primary,
  },
]

export function DocumentAnalysisProgress({ fileCount }: DocumentAnalysisProgressProps) {
  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0)
  const [phaseProgress, setPhaseProgress] = useState(0)
  const [elapsedTime, setElapsedTime] = useState(0)

  const currentPhase = PHASES[currentPhaseIndex]
  const totalPhases = PHASES.length

  useEffect(() => {
    // Progress bar animation within each phase
    const progressInterval = setInterval(() => {
      setPhaseProgress((prev) => {
        if (prev >= 100) {
          // Move to next phase
          if (currentPhaseIndex < PHASES.length - 1) {
            setCurrentPhaseIndex((idx) => idx + 1)
            return 0
          }
          return 100
        }
        // Smooth progress increment based on phase duration
        const phaseDuration = PHASE_DURATIONS[currentPhase.id as keyof typeof PHASE_DURATIONS] || 5000
        const increment = (100 / phaseDuration) * 100 // 100ms interval
        return Math.min(prev + increment, 100)
      })
    }, 100)

    // Elapsed time counter
    const timeInterval = setInterval(() => {
      setElapsedTime((t) => t + 1)
    }, 1000)

    return () => {
      clearInterval(progressInterval)
      clearInterval(timeInterval)
    }
  }, [currentPhaseIndex, currentPhase.id])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
  }

  return (
    <div className="space-y-6 py-8">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center space-x-3">
          <div className="relative">
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center text-3xl animate-pulse"
              style={{
                backgroundColor: `${currentPhase.color}20`,
                borderColor: currentPhase.color,
                borderWidth: '3px',
              }}
            >
              {currentPhase.icon}
            </div>
            {/* Spinning ring */}
            <div
              className="absolute inset-0 rounded-full border-4 border-transparent animate-spin"
              style={{
                borderTopColor: currentPhase.color,
                borderRightColor: currentPhase.color,
              }}
            />
          </div>
        </div>

        <h3
          className="text-xl font-semibold"
          style={{ color: currentPhase.color }}
        >
          {currentPhase.label}
        </h3>

        <p
          className="text-sm"
          style={{ color: designTokens.colors.neutral[600] }}
        >
          {currentPhase.description}
        </p>

        <p
          className="text-xs font-mono"
          style={{ color: designTokens.colors.neutral[500] }}
        >
          Processing {fileCount} {fileCount === 1 ? 'file' : 'files'} • {formatTime(elapsedTime)}
        </p>
      </div>

      {/* Phase Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs font-medium" style={{ color: designTokens.colors.neutral[600] }}>
          <span>Phase {currentPhaseIndex + 1} of {totalPhases}</span>
          <span>{Math.round(phaseProgress)}%</span>
        </div>

        <div
          className="w-full h-2 rounded-full overflow-hidden"
          style={{ backgroundColor: designTokens.colors.neutral[200] }}
        >
          <div
            className="h-full rounded-full transition-all duration-300 ease-out"
            style={{
              width: `${phaseProgress}%`,
              backgroundColor: currentPhase.color,
            }}
          />
        </div>
      </div>

      {/* Overall Progress Timeline */}
      <div className="flex justify-between items-center px-4">
        {PHASES.map((phase, index) => {
          const isPast = index < currentPhaseIndex
          const isCurrent = index === currentPhaseIndex
          const isFuture = index > currentPhaseIndex

          return (
            <div key={phase.id} className="flex flex-col items-center space-y-2 flex-1">
              {/* Circle indicator */}
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-lg border-2 transition-all duration-300 ${
                  isCurrent ? 'scale-110' : ''
                }`}
                style={{
                  backgroundColor: isPast || isCurrent ? phase.color : designTokens.colors.neutral[100],
                  borderColor: isPast || isCurrent ? phase.color : designTokens.colors.neutral[300],
                  color: isPast || isCurrent ? '#ffffff' : designTokens.colors.neutral[400],
                }}
              >
                {isPast ? '✓' : phase.icon}
              </div>

              {/* Label */}
              <span
                className="text-xs text-center font-medium"
                style={{
                  color: isPast || isCurrent ? phase.color : designTokens.colors.neutral[400],
                }}
              >
                {phase.label}
              </span>

              {/* Connecting line (except for last phase) */}
              {index < PHASES.length - 1 && (
                <div
                  className="absolute h-0.5 top-5 transition-all duration-300"
                  style={{
                    left: `${((index + 0.5) / PHASES.length) * 100}%`,
                    width: `${(1 / PHASES.length) * 100}%`,
                    backgroundColor: isPast ? phase.color : designTokens.colors.neutral[300],
                  }}
                />
              )}
            </div>
          )
        })}
      </div>

      {/* Tips */}
      <div
        className="text-xs text-center p-4 rounded-lg"
        style={{
          backgroundColor: designTokens.colors.neutral[50],
          color: designTokens.colors.neutral[600],
        }}
      >
        <p className="flex items-center justify-center space-x-2">
          <span>💡</span>
          <span>
            {currentPhaseIndex === 0
              ? 'Files are being scanned for security threats...'
              : 'Analyzing document content and extracting keywords...'}
          </span>
        </p>
      </div>
    </div>
  )
}
