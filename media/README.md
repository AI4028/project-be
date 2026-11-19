# Photos

Store and menu photos, served at `/media/...`.

1. Put files in a folder per store: `media/gist-cafe/store.jpg`, `media/gist-cafe/americano.jpg`.
2. Point the seed file at them:
   - store: `"imageUrl": "/media/gist-cafe/store.jpg"` inside `store`
   - menu item: `"imageUrl": "/media/gist-cafe/americano.jpg"`
3. Re-run the seed script. It stops if a file is missing.

Use JPG or WebP, about 800 px wide and under 200 KB. Only use photos you took or have permission to use.
