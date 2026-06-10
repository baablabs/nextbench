#!/usr/bin/env python3
"""Fix the 11 actually-broken source URLs surfaced by the v0.2 audit.

The audit's first pass used HEAD requests which several CDNs reject; the
re-check with a browser UA + GET fallback narrowed 47 flags down to 11
real 404s / timeouts. This script swaps each broken URL with its closest
known-good canonical equivalent.

Replacements:
  - lucia-auth.com (deprecated/reorganized) → Auth.js docs equivalents
  - owasp.org/www-community/* → owasp.org/API-Security or
    cheatsheetseries.owasp.org/cheatsheets (the modern home)
  - nextjs.org draftMode camelCase → kebab-case (Next.js renamed routes)
  - nextjs.org template under routing → under file-conventions
  - kentcdodds.com compound components blog (timeout) → React docs equiv
  - totaltypescript.com generic-functions (404) → official TS handbook
  - mdn Element/contains → Node/contains (interface moved)
  - aws.amazon.com/blogs/ preSigned URLs → docs.aws.amazon.com canonical
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"

# Old -> New URL map.
URL_FIXES = {
    "https://aws.amazon.com/blogs/aws/amazon-s3-presigned-urls/":
        "https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html",
    "https://developer.mozilla.org/en-US/docs/Web/API/Element/contains":
        "https://developer.mozilla.org/en-US/docs/Web/API/Node/contains",
    "https://kentcdodds.com/blog/compound-components-with-react-hooks":
        "https://react.dev/learn/passing-data-deeply-with-context",
    "https://lucia-auth.com/guides/email-and-password/email-verification":
        "https://authjs.dev/getting-started/authentication/email",
    "https://lucia-auth.com/sessions/cookies":
        "https://authjs.dev/concepts/session-strategies",
    "https://nextjs.org/docs/app/api-reference/functions/draftMode":
        "https://nextjs.org/docs/app/api-reference/functions/draft-mode",
    "https://nextjs.org/docs/app/building-your-application/routing/template":
        "https://nextjs.org/docs/app/api-reference/file-conventions/template",
    "https://owasp.org/www-community/Broken_Object_Level_Authorization":
        "https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/",
    "https://owasp.org/www-community/Forgot_Password_Cheat_Sheet":
        "https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html",
    "https://owasp.org/www-community/Logging_Cheat_Sheet":
        "https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html",
    "https://www.totaltypescript.com/concepts/generic-functions":
        "https://www.typescriptlang.org/docs/handbook/2/generics.html",
}


def main() -> None:
    n_swapped = 0
    files_touched = 0
    for fp in sorted(TASKS_DIR.glob("*.jsonl")):
        rows = []
        touched = False
        with open(fp) as f:
            for line in f:
                if not line.strip():
                    continue
                t = json.loads(line)
                url = t.get("metadata", {}).get("source_url")
                if url in URL_FIXES:
                    t["metadata"]["source_url"] = URL_FIXES[url]
                    n_swapped += 1
                    touched = True
                rows.append(t)
        if touched:
            files_touched += 1
            with open(fp, "w") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Swapped {n_swapped} source URLs across {files_touched} files.")


if __name__ == "__main__":
    main()
