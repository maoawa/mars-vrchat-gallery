import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { basename, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const dataDir = fileURLToPath(new URL('./src/data', import.meta.url))
const tagsFile = join(dataDir, 'tags.json')

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

  return {
    name: 'expose-gallery-data',
    configResolved(config) {
      outputDataDir = resolve(config.root, config.build.outDir, 'data')
    },
    configureServer(server) {
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

          writeFileSync(tagsFile, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
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
