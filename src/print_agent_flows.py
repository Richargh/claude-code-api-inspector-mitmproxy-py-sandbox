from textwrap import shorten
from pathlib import Path

from internal.colors import RED, RESET, Colorize
from internal.flows import parse_flow, RequestFlow, ResponseFlow
from datetime import datetime
from internal.print_request import print_request
from internal.print_response import _print_response
from internal.flow_config import FlowConfig


def response(raw_flow, config: FlowConfig = FlowConfig()) -> None:
    req_flow, res_flow = parse_flow(raw_flow)
    raw_request_file, raw_response_file = _write_trace(raw_flow, req_flow, res_flow)

    if req_flow.error:
        print(f"{RED}# Request Error:{RESET} {shorten(raw_flow.request.text, width=1000, placeholder='...')}")
        return

    if raw_flow.request:
        print_request(req_flow, config)

    if raw_flow.response:
        _print_response(raw_flow, res_flow)

    print(f"\n# Raw Traces")
    print(f"Written raw request to {raw_request_file}")
    print(f"Written raw response to {raw_response_file}")


def _write_trace(raw_flow, req_flow: RequestFlow, res_flow: ResponseFlow) -> tuple[Path, Path]:
    now = datetime.now().isoformat()
    raw_request_file = Path(__file__).parent.parent / 'trace' / f"{now}-req.json"
    raw_response_file = Path(__file__).parent.parent / 'trace' / f"{now}-res.json"
    if req_flow.pretty:
        with open(raw_request_file, "w") as f:
            f.write(req_flow.pretty)
    elif raw_flow.request:
        print("Pretty request is missing")
        with open(raw_response_file, "w") as f:
            f.write(raw_flow.request.text)

    if res_flow.pretty:
        with open(raw_response_file, "w") as f:
            f.write(res_flow.pretty)
    elif raw_flow.response:
        print("Pretty response is missing")
        with open(raw_response_file, "w") as f:
            f.write(raw_flow.response.text)
    return raw_request_file, raw_response_file
