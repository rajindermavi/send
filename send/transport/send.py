from email.message import EmailMessage
from pathlib import Path

from send.common.config import Backend
from send.transport.dry_run_transport import DryRunTransport
from send.transport.google_transport import GoogleTransport
from send.transport.ms_graph_transport import MSGraphTransport


def send(cfg: dict, msg: EmailMessage, backend: Backend, **kw) -> None:
    if backend == "ms_graph":
        MSGraphTransport.send_email_from_config(cfg, msg, **kw)
    elif backend == "google_api":
        GoogleTransport.send_email_from_config(cfg, msg, **kw)
    elif backend == "dry_run":
        out_dir = (cfg or {}).get("out_dir")
        if not out_dir:
            raise ValueError("dry_run backend requires 'out_dir' in cfg.")
        transport = DryRunTransport(Path(out_dir), write_metadata=kw.get("write_metadata", True))
        transport.send_email_from_config(msg,**kw)
    else:
        raise ValueError(f"Unknown backend: {backend}")
