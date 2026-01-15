// frontend/src/app/robots.ts
import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          '/api/',
          '/dashboard',
          '/dashboard/*',
          '/documents',
          '/documents/*',
          '/categories',
          '/categories/*',
          '/profile',
          '/profile/*',
          '/settings',
          '/settings/*',
          '/admin',
          '/admin/*',
          '/delegates',
          '/delegates/*',
          '/auth/*',
          '/callback/*',
        ],
      },
    ],
    sitemap: 'https://bonidoc.com/sitemap.xml',
  }
}
