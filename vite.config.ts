import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { basename, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const dataDir = fileURLToPath(new URL('./src/data', import.meta.url))
const tagsFile = join(dataDir, 'tags.json')
const imagesFile = join(dataDir, 'images.json')
const friendsFile = join(dataDir, 'friends.json')
const worldsFile = join(dataDir, 'worlds.json')

type TagPayload = Array<{
  photo: number
  tags: Array<{
    friend: string
    x: number
    y: number
    position?: 'top' | 'right' | 'bottom' | 'left'
  }>
}>

function isTagPayload(value: unknown): value is TagPayload {
  if (!Array.isArray(value)) {
    return false
  }

  return value.every((group) => {
    if (!group || typeof group !== 'object') {
      return false
    }

    const record = group as Record<string, unknown>

    if (!Number.isFinite(record.photo) || !Array.isArray(record.tags)) {
      return false
    }

    return record.tags.every((tag) => {
      if (!tag || typeof tag !== 'object') {
        return false
      }

      const tagRecord = tag as Record<string, unknown>
      const position = tagRecord.position

      return (
        typeof tagRecord.friend === 'string' &&
        Number.isFinite(tagRecord.x) &&
        Number.isFinite(tagRecord.y) &&
        (position === undefined || position === 'top' || position === 'right' || position === 'bottom' || position === 'left')
      )
    })
  })
}

function isNamedEntityPayload(value: unknown) {
  return (
    Array.isArray(value) &&
    value.every((item) => {
      if (!item || typeof item !== 'object') {
        return false
      }

      const record = item as Record<string, unknown>
      return (
        typeof record.id === 'string' &&
        record.id.trim().length > 0 &&
        typeof record.name_en === 'string' &&
        (record.name_zh === undefined || typeof record.name_zh === 'string') &&
        (record.link === undefined || typeof record.link === 'string')
      )
    })
  )
}

function isImagePayload(value: unknown) {
  return (
    Array.isArray(value) &&
    value.every((item) => {
      if (!item || typeof item !== 'object') {
        return false
      }

      const record = item as Record<string, unknown>
      return (
        Number.isFinite(record.id) &&
        typeof record.filename === 'string' &&
        typeof record.captured === 'string' &&
        typeof record.world === 'string' &&
        Array.isArray(record.friend) &&
        record.friend.every((friendId) => typeof friendId === 'string') &&
        (record.linked === undefined ||
          (Array.isArray(record.linked) && record.linked.every((photoId) => Number.isFinite(photoId)))) &&
        (record.parent === undefined || Number.isFinite(record.parent))
      )
    })
  )
}

function isGalleryPayload(value: unknown): value is {
  images: unknown[]
  friends: unknown[]
  worlds: unknown[]
  tags: TagPayload
} {
  if (!value || typeof value !== 'object') {
    return false
  }

  const record = value as Record<string, unknown>
  return (
    isImagePayload(record.images) &&
    isNamedEntityPayload(record.friends) &&
    isNamedEntityPayload(record.worlds) &&
    isTagPayload(record.tags)
  )
}

function dumpJson(value: unknown, indent = 0): string {
  const space = ' '.repeat(indent)
  const childSpace = ' '.repeat(indent + 2)

  if (Array.isArray(value)) {
    if (!value.length) return '[]'
    if (value.every((item) => item === null || typeof item !== 'object')) {
      return `[${value.map((item) => JSON.stringify(item)).join(', ')}]`
    }

    return [
      '[',
      ...value.map(
        (item, index) => `${childSpace}${dumpJson(item, indent + 2)}${index < value.length - 1 ? ',' : ''}`,
      ),
      `${space}]`,
    ].join('\n')
  }

  if (value && typeof value === 'object') {
    const entries = Object.entries(value)
    if (!entries.length) return '{}'

    return [
      '{',
      ...entries.map(
        ([key, item], index) =>
          `${childSpace}${JSON.stringify(key)}: ${dumpJson(item, indent + 2)}${index < entries.length - 1 ? ',' : ''}`,
      ),
      `${space}}`,
    ].join('\n')
  }

  return JSON.stringify(value)
}

function writeJsonFile(filePath: string, payload: unknown) {
  writeFileSync(filePath, `${dumpJson(payload)}\n`, 'utf8')
}

function readRequestBody(request: import('node:http').IncomingMessage) {
  return new Promise<string>((resolveBody, rejectBody) => {
    let body = ''

    request.setEncoding('utf8')
    request.on('data', (chunk) => {
      body += chunk
    })
    request.on('end', () => resolveBody(body))
    request.on('error', rejectBody)
  })
}

function exposeGalleryData(): Plugin {
  let outputDataDir = ''
  const editorSavedFiles = new Map<string, number>()

  function writeEditorJsonFile(filePath: string, payload: unknown) {
    editorSavedFiles.set(resolve(filePath), Date.now())
    writeJsonFile(filePath, payload)
  }

  return {
    name: 'expose-gallery-data',
    configResolved(config) {
      outputDataDir = resolve(config.root, config.build.outDir, 'data')
    },
    handleHotUpdate(context) {
      const filePath = resolve(context.file)
      const savedAt = editorSavedFiles.get(filePath)

      if (savedAt && Date.now() - savedAt < 3_000) {
        return []
      }

      if (savedAt) editorSavedFiles.delete(filePath)
    },
    configureServer(server) {
      server.middlewares.use('/__gallery/save', async (request, response, next) => {
        if (request.method !== 'POST') {
          next()
          return
        }

        try {
          const body = await readRequestBody(request)
          const payload = JSON.parse(body) as unknown

          if (!isGalleryPayload(payload)) {
            response.statusCode = 400
            response.end('Invalid gallery payload')
            return
          }

          writeEditorJsonFile(imagesFile, payload.images)
          writeEditorJsonFile(friendsFile, payload.friends)
          writeEditorJsonFile(worldsFile, payload.worlds)
          writeEditorJsonFile(tagsFile, payload.tags)
          response.setHeader('Content-Type', 'application/json; charset=utf-8')
          response.end(JSON.stringify({ ok: true }))
        } catch (error) {
          response.statusCode = 500
          response.end(error instanceof Error ? error.message : 'Failed to save gallery data')
        }
      })

      server.middlewares.use('/__tags/save', async (request, response, next) => {
        if (request.method !== 'POST') {
          next()
          return
        }

        try {
          const body = await readRequestBody(request)
          const payload = JSON.parse(body) as unknown

          if (!isTagPayload(payload)) {
            response.statusCode = 400
            response.end('Invalid tag payload')
            return
          }

          writeEditorJsonFile(tagsFile, payload)
          response.setHeader('Content-Type', 'application/json; charset=utf-8')
          response.end(JSON.stringify({ ok: true }))
        } catch (error) {
          response.statusCode = 500
          response.end(error instanceof Error ? error.message : 'Failed to save tags')
        }
      })

      server.middlewares.use('/data', (request, response, next) => {
        const fileName = basename(request.url?.split('?')[0] ?? '')

        if (!fileName.endsWith('.json')) {
          next()
          return
        }

        const filePath = join(dataDir, fileName)

        if (!existsSync(filePath)) {
          next()
          return
        }

        response.setHeader('Content-Type', 'application/json; charset=utf-8')
        response.end(readFileSync(filePath))
      })
    },
    closeBundle() {
      mkdirSync(outputDataDir, { recursive: true })

      readdirSync(dataDir)
        .filter((fileName) => fileName.endsWith('.json'))
        .forEach((fileName) => {
          copyFileSync(join(dataDir, fileName), join(outputDataDir, fileName))
        })
    },
  }
}

export default defineConfig({
  define: {
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
  plugins: [vue(), exposeGalleryData()],
})
