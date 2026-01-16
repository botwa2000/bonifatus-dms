const sharp = require('sharp');
const path = require('path');
const fs = require('fs');

const assetsDir = path.join(__dirname, '..', '..', 'assets');
const publicDir = path.join(__dirname, '..', 'public');

async function optimizeLogo() {
  console.log('=== Optimizing Logo ===');

  const sourceLogo = path.join(assetsDir, 'A3.png');

  // Create optimized versions of the full logo (with text)
  // Header logo - 400px wide
  await sharp(sourceLogo)
    .resize(400, null, { withoutEnlargement: true })
    .png({ quality: 90, compressionLevel: 9 })
    .toFile(path.join(publicDir, 'logo-header.png'));
  console.log('✓ Created logo-header.png (400px wide)');

  // Also create WebP version for better compression
  await sharp(sourceLogo)
    .resize(400, null, { withoutEnlargement: true })
    .webp({ quality: 90 })
    .toFile(path.join(publicDir, 'logo-header.webp'));
  console.log('✓ Created logo-header.webp (400px wide)');

  // Medium logo for other uses - 200px wide
  await sharp(sourceLogo)
    .resize(200, null, { withoutEnlargement: true })
    .png({ quality: 90, compressionLevel: 9 })
    .toFile(path.join(publicDir, 'logo-medium.png'));
  console.log('✓ Created logo-medium.png (200px wide)');

  // Update main logo.png with optimized version (512px)
  await sharp(sourceLogo)
    .resize(512, null, { withoutEnlargement: true })
    .png({ quality: 90, compressionLevel: 9 })
    .toFile(path.join(publicDir, 'logo.png'));
  console.log('✓ Updated logo.png (512px wide)');
}

async function createFavicons() {
  console.log('\n=== Creating Favicons ===');

  const sourceIcon = path.join(assetsDir, 'F5.png');

  // Create PNG favicons at various sizes
  const sizes = [16, 32, 48, 64, 96, 128, 192, 256, 512];

  for (const size of sizes) {
    await sharp(sourceIcon)
      .resize(size, size)
      .png({ quality: 90, compressionLevel: 9 })
      .toFile(path.join(publicDir, `favicon-${size}x${size}.png`));
    console.log(`✓ Created favicon-${size}x${size}.png`);
  }

  // Create apple-touch-icon (180x180)
  await sharp(sourceIcon)
    .resize(180, 180)
    .png({ quality: 90, compressionLevel: 9 })
    .toFile(path.join(publicDir, 'apple-touch-icon.png'));
  console.log('✓ Created apple-touch-icon.png (180x180)');

  // Create android-chrome icons
  await sharp(sourceIcon)
    .resize(192, 192)
    .png({ quality: 90, compressionLevel: 9 })
    .toFile(path.join(publicDir, 'android-chrome-192x192.png'));
  console.log('✓ Created android-chrome-192x192.png');

  await sharp(sourceIcon)
    .resize(512, 512)
    .png({ quality: 90, compressionLevel: 9 })
    .toFile(path.join(publicDir, 'android-chrome-512x512.png'));
  console.log('✓ Created android-chrome-512x512.png');

  // Create ICO file with multiple sizes embedded
  // Sharp doesn't support ICO directly, so we'll create the PNG files
  // and the user can use an online converter or we'll reference PNGs

  // Create a 32x32 PNG as the main favicon fallback
  await sharp(sourceIcon)
    .resize(32, 32)
    .png({ quality: 90, compressionLevel: 9 })
    .toFile(path.join(publicDir, 'favicon.png'));
  console.log('✓ Created favicon.png (32x32)');
}

async function createWebManifest() {
  console.log('\n=== Creating Web Manifest ===');

  const manifest = {
    name: 'Bonifatus DMS',
    short_name: 'Bonidoc',
    description: 'AI-Powered Document Management System',
    start_url: '/',
    display: 'standalone',
    background_color: '#ffffff',
    theme_color: '#2563eb',
    icons: [
      {
        src: '/android-chrome-192x192.png',
        sizes: '192x192',
        type: 'image/png'
      },
      {
        src: '/android-chrome-512x512.png',
        sizes: '512x512',
        type: 'image/png'
      },
      {
        src: '/android-chrome-512x512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'maskable'
      }
    ]
  };

  fs.writeFileSync(
    path.join(publicDir, 'site.webmanifest'),
    JSON.stringify(manifest, null, 2)
  );
  console.log('✓ Created site.webmanifest');
}

async function main() {
  try {
    await optimizeLogo();
    await createFavicons();
    await createWebManifest();

    console.log('\n=== Done! ===');
    console.log('All logo and favicon files have been created in frontend/public/');
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

main();
