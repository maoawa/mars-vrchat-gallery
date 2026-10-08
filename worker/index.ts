export interface Env extends Cloudflare.Env {
  STEAM_API_KEY?: string
  STEAM_ID?: string
}

const VRCHAT_APP_ID = 438100
const CACHE_TTL_SECONDS = 15 * 60

function corsHeaders(request: Request, env: Env) {
  const origin = request.headers.get('Origin')
  const allowedOrigins: string[] = [...env.ALLOWED_ORIGINS, 'http://localhost:5173', 'http://localhost:5174']
  const allowedOrigin = origin && allowedOrigins.includes(origin) ? origin : allowedOrigins[0]

  return {
    'Access-Control-Allow-Origin': allowedOrigin,
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    Vary: 'Origin',
  }
}

function jsonResponse(request: Request, env: Env, body: unknown, status = 200, cacheControl = 'no-store') {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': cacheControl,
      ...corsHeaders(request, env),
    },
  })
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url)

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(request, env) })
    }

    if (request.method !== 'GET' || url.pathname !== '/api/steam-playtime') {
      return jsonResponse(request, env, { error: 'Not found' }, 404)
    }

    if (!env.STEAM_API_KEY || !env.STEAM_ID) {
      return jsonResponse(request, env, { error: 'Steam API is not configured' }, 503)
    }

    const cache = caches.default
    const cacheKey = new Request(`${url.origin}/api/steam-playtime`, request)
    const cached = await cache.match(cacheKey)
    if (cached) {
      const response = new Response(cached.body, cached)
      for (const [name, value] of Object.entries(corsHeaders(request, env))) {
        response.headers.set(name, value)
      }
      return response
    }

    const steamUrl = new URL('https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/')
    steamUrl.searchParams.set('key', env.STEAM_API_KEY)
    steamUrl.searchParams.set('steamid', env.STEAM_ID)
    steamUrl.searchParams.set('format', 'json')
    steamUrl.searchParams.set('include_appinfo', 'false')
    steamUrl.searchParams.set('include_played_free_games', 'true')

    const steamResponse = await fetch(steamUrl)
    if (!steamResponse.ok) {
      return jsonResponse(request, env, { error: 'Steam API request failed' }, 502)
    }

    const payload = (await steamResponse.json()) as {
      response?: { games?: Array<{ appid: number; playtime_forever?: number }> }
    }
    const game = payload.response?.games?.find((entry) => entry.appid === VRCHAT_APP_ID)
    if (!game) {
      return jsonResponse(request, env, { error: 'VRChat playtime is unavailable' }, 404)
    }

    const body = JSON.stringify({
      appId: VRCHAT_APP_ID,
      playtimeHours: Number(((game.playtime_forever ?? 0) / 60).toFixed(1)),
      fetchedAt: new Date().toISOString(),
    })
    const response = new Response(body, {
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': `public, max-age=${CACHE_TTL_SECONDS}`,
        ...corsHeaders(request, env),
      },
    })
    ctx.waitUntil(cache.put(cacheKey, response.clone()))
    return response
  },
} satisfies ExportedHandler<Env>
