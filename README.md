# The Black Whale

This branch is focused on user capabilities, cart functions, inventory functions, and item-related flows.

## Branch Merge Compatibility

The frontend now supports two runtime modes through `app.config.js`:

- `dataMode: "local"` uses local in-memory data for development.
- `dataMode: "api"` uses backend endpoints for MySQL-backed data.

Set `apiBaseUrl` in `app.config.js` when your backend branch is ready.

## Shared Runtime Files

- `app.config.js`: app-wide runtime config consumed by cart and inventory pages.
- `function.js`: cart logic with local/API adapter and graceful fallback.
- `inventory.js`: inventory and purchase logic with local/API adapter and graceful fallback.
- `styles/cart.css` and `styles/inventory.css`: extracted page styles to reduce conflicts with CSS branch work.

## Backend API Contract (for MySQL branch)

Cart endpoints expected by `function.js`:

- `POST /api/cart/items` body: `{ itemId, quantity }`
- `PATCH /api/cart/items/:id` body: `{ quantityDelta }`
- `DELETE /api/cart`

Inventory endpoints expected by `inventory.js`:

- `GET /api/items` returns array or `{ items: [...] }`
- `POST /api/items` body: item payload
- `PATCH /api/items/:id` body: partial item payload
- `DELETE /api/items/:id`
- `GET /api/purchases` returns array or `{ purchases: [...] }`
- `POST /api/purchases` body: `{ itemId, quantity, buyer }`
- `GET /api/inventory/stats` optional (frontend can calculate if unavailable)

## Merge Notes

- Keep DOM element IDs stable in templates to avoid JS conflicts.
- Keep API paths stable, or update them in one place through `app.config.js` and adapter functions.
- Keep page styles in CSS files rather than inline `<style>` blocks to reduce merge overlap.

Team includes Adonis Pearson, Ishaan Hopkins, Kayron Brown, and Byron Jones.
