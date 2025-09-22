// src/utils/cn.ts
/**
 * Utility for merging class names with Tailwind CSS
 * Handles conditional classes and removes conflicts
 */

import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}