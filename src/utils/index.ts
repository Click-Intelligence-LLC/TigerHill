import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds?: number): string {
  if (!seconds) return '0s';
  
  if (seconds < 60) {
    return `${seconds}s`;
  } else if (seconds < 3600) {
    const minuteCount = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minuteCount}m ${remainingSeconds}s`;
  } else {
    const hourCount = Math.floor(seconds / 3600);
    const minuteCount = Math.floor((seconds % 3600) / 60);
    return `${hourCount}h ${minuteCount}m`;
  }
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'success':
      return 'text-green-600 bg-green-100';
    case 'error':
      return 'text-red-600 bg-red-100';
    case 'timeout':
      return 'text-yellow-600 bg-yellow-100';
    case 'cancelled':
      return 'text-gray-600 bg-gray-100';
    default:
      return 'text-blue-600 bg-blue-100';
  }
}

export function getTurnTypeIcon(type: string): string {
  switch (type) {
    case 'user_input':
      return '👤';
    case 'ai_response':
      return '🤖';
    case 'tool_call':
      return '🔧';
    case 'error':
      return '❌';
    case 'function_return':
      return '↩️';
    default:
      return '💬';
  }
}
