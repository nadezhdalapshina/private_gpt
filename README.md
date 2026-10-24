# Spain itinerary: automatic photo download

You do not need to download 68 images manually.

1. Upload `index.html`, `fetch_photos.py`, and `.github/workflows/photos.yml` into your GitHub Pages repository. (Preserve the `.github/workflows/` folder structure.)
2. In GitHub: **Actions** → **Download itinerary photos** → **Run workflow**.
3. The workflow searches Wikimedia Commons, downloads candidate photos into `images/`, rewrites HTML to point at local files and commits the result. In repository Settings → Actions → General → Workflow permissions, enable **Read and write permissions** if commits are blocked.
4. Check `PHOTO_REVIEW.csv`: computer-selected images can be incorrect, and not every Wikimedia photo may be downloadable. Image attribution source links are inserted below downloaded pictures.
5. GitHub Pages deploys again after the updated files are committed. The `images/` folder is now in the repository.

Note: this uses title keyword matching, not human visual verification. It avoids replacing unknown photos with repeated generic location images, but it cannot guarantee every result is accurate. For perfect 68/68 accurate photos, review and curate candidates. Do not publish unverified attribution/licensing without checking each file's Commons page.
