/**
 * Audio Compression and Recording Utility
 * Optimizes audio recording with better codecs and compression
 */

interface AudioRecorderOptions {
  mimeType?: string
  audioBitsPerSecond?: number
  sampleRate?: number
}

/**
 * Gets the best supported audio MIME type
 */
export function getBestAudioMimeType(): string {
  const types = [
    'audio/webm;codecs=opus', // Best compression, widely supported
    'audio/webm', // Fallback for WebM
    'audio/ogg;codecs=opus', // Opus in Ogg container
    'audio/mp4', // MP4 audio
    'audio/webm;codecs=vp9', // VP9 codec
    'audio/wav' // Uncompressed fallback
  ]

  for (const type of types) {
    if (MediaRecorder.isTypeSupported(type)) {
      return type
    }
  }

  return 'audio/webm' // Default fallback
}

/**
 * Creates an optimized MediaRecorder instance
 */
export async function createOptimizedRecorder(
  stream: MediaStream,
  options: AudioRecorderOptions = {}
): Promise<MediaRecorder> {
  const mimeType = options.mimeType || getBestAudioMimeType()

  const recorderOptions: MediaRecorderOptions = {
    mimeType,
    audioBitsPerSecond: options.audioBitsPerSecond || 64000 // 64kbps - good quality, small size
  }

  // Apply audio constraints for better quality
  const audioTrack = stream.getAudioTracks()[0]
  if (audioTrack) {
    await audioTrack.applyConstraints({
      sampleRate: options.sampleRate || 48000, // 48kHz sample rate
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true
    })
  }

  return new MediaRecorder(stream, recorderOptions)
}

/**
 * Compresses audio blob if needed
 * For WebM/Opus this is already efficient, so we mainly validate and convert if needed
 */
export async function compressAudioBlob(
  blob: Blob,
  targetFormat: string = 'audio/webm;codecs=opus'
): Promise<Blob> {
  // If already in target format and small enough, return as-is
  if (blob.type === targetFormat || blob.size < 100000) {
    // Less than 100KB
    return blob
  }

  // For now, return the blob as-is since WebM Opus is already well compressed
  // In future, could implement additional compression using Web Audio API
  return blob
}

/**
 * Estimates recording duration from blob
 */
export function estimateDuration(blob: Blob, bitrate: number = 64000): number {
  const bytes = blob.size
  const bits = bytes * 8
  const seconds = bits / bitrate
  return Math.round(seconds)
}

/**
 * Formats duration in MM:SS format
 */
export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

/**
 * Gets audio file extension from MIME type
 */
export function getAudioExtension(mimeType: string): string {
  if (mimeType.includes('webm')) return 'webm'
  if (mimeType.includes('ogg')) return 'ogg'
  if (mimeType.includes('mp4') || mimeType.includes('m4a')) return 'm4a'
  if (mimeType.includes('wav')) return 'wav'
  return 'webm' // default
}

/**
 * Creates a downloadable audio file name
 */
export function createAudioFileName(prefix: string = 'recording'): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
  const mimeType = getBestAudioMimeType()
  const ext = getAudioExtension(mimeType)
  return `${prefix}_${timestamp}.${ext}`
}

/**
 * Format bytes to human-readable size
 */
export function formatAudioSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

/**
 * Validates audio blob
 */
export function isValidAudioBlob(blob: Blob): boolean {
  return blob.size > 0 && blob.type.startsWith('audio/')
}

/**
 * Gets recording quality info
 */
export function getRecordingQuality(bitrate: number): {
  quality: 'low' | 'medium' | 'high' | 'very_high'
  description: string
} {
  if (bitrate < 32000) {
    return { quality: 'low', description: 'Niska jakość (rozmowy)' }
  } else if (bitrate < 64000) {
    return { quality: 'medium', description: 'Średnia jakość (podcasty)' }
  } else if (bitrate < 128000) {
    return { quality: 'high', description: 'Wysoka jakość (muzyka)' }
  } else {
    return { quality: 'very_high', description: 'Bardzo wysoka jakość (studio)' }
  }
}
