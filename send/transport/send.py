from email.message import EmailMessage
from pathlib import Path

from send.common.config import Backend
from send.transport.dry_run_transport import DryRunTransport
from send.transport.google_transport import GoogleTransport
from send.transport.ms_graph_transport import MSGraphTransport


def send(
    cfg: dict,
    msg: EmailMessage,
    backend: Backend,
    *,
    out_dir: Path | str | None = None,
    access_token: str | None = None,
    **kw,
) -> None:
    if backend == "ms_graph":
        MSGraphTransport.send_email_from_config(cfg, msg, access_token=access_token)
    elif backend == "google_api":
        GoogleTransport.send_email_from_config(cfg, msg, access_token=access_token)
    elif backend == "dry_run":
        if out_dir is None:
            raise ValueError("dry_run backend requires 'out_dir'.")
        out_path = Path(out_dir)
        transport = DryRunTransport(out_path, write_metadata=kw.get("write_metadata", True))
        transport.send_email_from_config(msg, **kw)
    else:
        raise ValueError(f"Unknown backend: {backend}")
