/**
 * Image Compression Utility
 * Compresses images client-side before upload to improve performance
 */

interface CompressionOptions {
  maxSizeMB?: number
  maxWidthOrHeight?: number
  quality?: number
  fileType?: string
}

const DEFAULT_OPTIONS: CompressionOptions = {
  maxSizeMB: 1, // Max 1MB
  maxWidthOrHeight: 1920, // Max dimension
  quality: 0.8, // 80% quality
  fileType: 'image/jpeg'
}

/**
 * Compresses an image file
 * @param file - The image file to compress
 * @param options - Compression options
 * @returns Compressed image file
 */
export async function compressImage(
  file: File,
  options: CompressionOptions = {}
): Promise<File> {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  // If file is already small enough, return it
  const fileSizeMB = file.size / 1024 / 1024
  if (fileSizeMB <= (opts.maxSizeMB || 1)) {
    return file
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = (e) => {
      const img = new Image()

      img.onload = () => {
        // Calculate new dimensions
        let { width, height } = img
        const maxDimension = opts.maxWidthOrHeight || 1920

        if (width > height) {
          if (width > maxDimension) {
            height = (height * maxDimension) / width
            width = maxDimension
          }
        } else {
          if (height > maxDimension) {
            width = (width * maxDimension) / height
            height = maxDimension
          }
        }

        // Create canvas and draw resized image
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height

        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('Could not get canvas context'))
          return
        }

        // Use better image smoothing
        ctx.imageSmoothingEnabled = true
        ctx.imageSmoothingQuality = 'high'

        // Draw image
        ctx.drawImage(img, 0, 0, width, height)

        // Convert to blob
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              reject(new Error('Canvas to Blob conversion failed'))
              return
            }

            // Create new file from blob
            const compressedFile = new File(
              [blob],
              file.name.replace(/\.\w+$/, '.jpg'),
              {
                type: opts.fileType || 'image/jpeg',
                lastModified: Date.now()
              }
            )

            resolve(compressedFile)
          },
          opts.fileType || 'image/jpeg',
          opts.quality || 0.8
        )
      }

      img.onerror = () => {
        reject(new Error('Failed to load image'))
      }

      img.src = e.target?.result as string
    }

    reader.onerror = () => {
      reject(new Error('Failed to read file'))
    }

    reader.readAsDataURL(file)
  })
}

/**
 * Gets compression statistics
 */
export function getCompressionStats(
  originalFile: File,
  compressedFile: File
): {
  originalSize: string
  compressedSize: string
  compressionRatio: string
  savedBytes: number
  savedPercentage: number
} {
  const originalBytes = originalFile.size
  const compressedBytes = compressedFile.size
  const savedBytes = originalBytes - compressedBytes
  const savedPercentage = ((savedBytes / originalBytes) * 100).toFixed(1)

  return {
    originalSize: formatBytes(originalBytes),
    compressedSize: formatBytes(compressedBytes),
    compressionRatio: `${((compressedBytes / originalBytes) * 100).toFixed(1)}%`,
    savedBytes,
    savedPercentage: parseFloat(savedPercentage)
  }
}

/**
 * Formats bytes to human-readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

/**
 * Validates if file is an image
 */
export function isValidImage(file: File): boolean {
  return file.type.startsWith('image/')
}

/**
 * Batch compress multiple images
 */
export async function compressImages(
  files: File[],
  options: CompressionOptions = {}
): Promise<File[]> {
  const promises = files.map((file) => compressImage(file, options))
  return Promise.all(promises)
}
