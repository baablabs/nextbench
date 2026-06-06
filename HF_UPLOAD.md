# Uploading NextBench to Hugging Face Hub

This makes `load_dataset("baablabs/nextbench")` work for everyone.

## One-time prerequisites

1. **Install the HF Hub CLI** (if not already):
   ```bash
   pip install -U huggingface_hub
   ```

2. **Authenticate with HF Hub** (one-time, opens browser):
   ```bash
   huggingface-cli login
   ```
   Paste a write-scoped token from https://huggingface.co/settings/tokens — pick **Write** access, name it `nextbench-upload` or similar.

3. **Create the `baablabs` HF organization** (free, match the GitHub name):
   - Go to https://huggingface.co/organizations/new
   - Name: **`baablabs`**
   - Logo (optional, can add later)
   - Skip "invite members"

## Upload

```bash
# Dry-run first (lists files, no upload):
python nextbench/scripts/upload_to_hf.py --dry-run

# Real upload to baablabs/nextbench:
python nextbench/scripts/upload_to_hf.py
```

The script:
- Uploads everything in `nextbench/` except `.git/`, `__pycache__/`, `.DS_Store`
- Pushes JSONL task files into HF Hub splits (one per category)
- Renders the README.md as the dataset card (frontmatter is already configured)
- Creates the dataset repo if it doesn't exist

## Verify

After upload, the dataset should be live at:
- **https://huggingface.co/datasets/baablabs/nextbench**

Test the load from any Python environment:

```python
from datasets import load_dataset

# Load all categories combined:
ds = load_dataset("baablabs/nextbench")

# Load a single category split:
react_tasks = load_dataset("baablabs/nextbench", split="react")

print(react_tasks[0]["task_id"])  # "react.avatar.021"
```

## Updating after task changes

After editing tasks, regenerating outputs, or any commit on GitHub:

```bash
# Push the GitHub commit first, then update HF Hub:
python nextbench/scripts/upload_to_hf.py --commit-message "Sync to vX.Y"
```

HF Hub keeps revision history (git-LFS underneath), so each upload is a versioned commit on the HF side too.

## Personal namespace testing

If you want to test the upload flow against your personal namespace first (recommended before pushing to the org):

```bash
python nextbench/scripts/upload_to_hf.py --dry-run --repo-id YOUR_USERNAME/nextbench
python nextbench/scripts/upload_to_hf.py --repo-id YOUR_USERNAME/nextbench
```

Once you verify it works, delete the personal copy and push to `baablabs/nextbench` for the real one.
