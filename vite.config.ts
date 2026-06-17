import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync } from 'node:fs'
import { basename, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const dataDir = fileURLToPath(new URL('./src/data', import.meta.url))

function exposeGalleryData(): Plugin {
  let outputDataDir = ''

  return {
    name: 'expose-gallery-data',
    configResolved(config) {
      outputDataDir = resolve(config.root, config.build.outDir, 'data')
    },
    configureServer(server) {
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
  plugins: [vue(), exposeGalleryData()],
})
