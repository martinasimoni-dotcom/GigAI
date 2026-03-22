"""
ACC RFI Poller — periodically checks ACC for new RFIs and feeds them into
the existing proposal pipeline (same path as a webhook would have triggered).

How it works:
  • On first run it records "now" as the watermark and does nothing (avoids
    re-processing historical RFIs on every restart).
  • On each subsequent tick it fetches RFIs created after the watermark,
    processes each new one through process_rfi_event(), then advances the
    watermark to the current time.
  • The watermark is kept in memory (process lifetime).  A restart causes
    at most one poll window of duplicate checks, which process_rfi_event
    handles gracefully (duplicate DB inserts are caught).
"""
import asyncio
from datetime import datetime, timezone, timedelta

from config import settings


class ACCPoller:
    def __init__(self, app):
        self.app          = app
        self.interval     = settings.POLLING_INTERVAL_MINUTES * 60  # seconds
        self._watermark:  datetime | None = None
        self._task:       asyncio.Task | None = None
        self._seen_ids:   set[str] = set()   # deduplicate within a run

    # ── Public API ────────────────────────────────────────────────────────

    def start(self):
        if not settings.POLLING_ENABLED:
            print("⏸  ACC poller disabled (POLLING_ENABLED=false)")
            return
        self._task = asyncio.create_task(self._loop())
        print(
            f"🔄 ACC poller started — checking every "
            f"{settings.POLLING_INTERVAL_MINUTES} min"
        )

    def stop(self):
        if self._task:
            self._task.cancel()

    # ── Internal ──────────────────────────────────────────────────────────

    async def _loop(self):
        # First tick: set watermark to now and skip processing so we don't
        # flood the pipeline with every existing RFI in the project.
        self._watermark = datetime.now(timezone.utc)
        print(f"   Watermark initialised: {self._watermark.isoformat()}")

        while True:
            await asyncio.sleep(self.interval)
            try:
                await self._poll()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Never let a poll error kill the loop
                print(f"⚠️  ACC poller error: {exc}")
                import traceback
                traceback.print_exc()

    async def _poll(self):
        from integrations.acc_client import ACCClient

        since     = self._watermark
        now       = datetime.now(timezone.utc)
        since_iso = since.isoformat() if since else ""

        print(f"\n🔍 ACC poll — checking for RFIs since {since_iso}")

        acc  = ACCClient()
        rfis = await acc.list_rfis(
            project_id=settings.ACC_PROJECT_ID,
            limit=50,
        )

        new_rfis = [r for r in rfis if self._is_new(r, since)]

        if not new_rfis:
            print(f"   No new RFIs found")
        else:
            print(f"   Found {len(new_rfis)} new RFI(s)")
            for rfi in new_rfis:
                rfi_id = rfi.get("id") or rfi.get("rfiId") or ""
                if not rfi_id or rfi_id in self._seen_ids:
                    continue
                self._seen_ids.add(rfi_id)
                print(f"   ▶ Queuing RFI {rfi_id}: {rfi.get('title', '(no title)')!r}")
                # Import here to avoid a circular import at module load time
                from api.webhooks import process_rfi_event
                asyncio.create_task(
                    process_rfi_event(
                        rfi_id=rfi_id,
                        project_id=settings.ACC_PROJECT_ID,
                        rfi_inline=rfi,
                        app=self.app,
                    )
                )

        # Advance watermark regardless of whether we found anything
        self._watermark = now

    def _is_new(self, rfi: dict, since: datetime) -> bool:
        """Return True if the RFI was created after *since*."""
        created_str = (
            rfi.get("createdAt")
            or rfi.get("created_at")
            or rfi.get("dateCreated")
            or ""
        )
        if not created_str:
            return False
        try:
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            return created > since
        except ValueError:
            return False
