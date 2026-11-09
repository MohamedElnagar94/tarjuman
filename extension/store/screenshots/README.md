# Store screenshots

The Chrome Web Store takes 1 to 5 screenshots, **1280×800** (preferred) or 640×400, PNG or JPEG, no alpha needed. The final set is taken by the lead; this folder holds working shots from `npm run shots`.

Suggested set (one language per listing; `.en` for the English listing, `.ar` for the Arabic one):

1. The overlay on a YouTube video: Arabic subtitles, bilingual line on, toolbar visible.
2. The overlay on a course site using the player's own captions.
3. The popup over a video page (compose the 360×580 popup onto a 1280×800 frame).
4. The options page (1280×800).
5. The welcome page with the connection found (1280×800).

Working files here:

| File | Size |
|---|---|
| `popup*.png` | 360×580, the popup at its natural size |
| `options.*.png`, `welcome.*.png` | 1280×800 |
| `overlay-*.png` | 1280×800, the overlay on a page |

Re-take them with a server running on 127.0.0.1:4318:

```sh
npm run build
node scripts/screenshots.mjs --lang=en --youtube="https://www.youtube.com/watch?v=jNQXAC9IVRw" --video=path/to/any.mp4
node scripts/screenshots.mjs --lang=ar --youtube="https://www.youtube.com/watch?v=jNQXAC9IVRw" --video=path/to/any.mp4
```

Avoid real people's faces or third-party branding you don't have rights to in the final store images.
