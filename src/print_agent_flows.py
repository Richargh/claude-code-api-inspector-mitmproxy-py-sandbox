from datetime import datetime
from pathlib import Path

from mitmproxy import http

from internal.flow_config import FlowConfig
from internal.format_request import format_request
from internal.format_response import format_response
from internal.parse_flows import RequestFlow, ResponseFlow, parse_flow

_DEFAULT_CONFIG = FlowConfig()


def response(raw_flow: http.HTTPFlow, config: FlowConfig = _DEFAULT_CONFIG) -> None:
    req_flow, res_flow = parse_flow(raw_flow)
    raw_request_file = None
    raw_response_file = None
    if config.write_trace:
        raw_request_file, raw_response_file = _write_trace(raw_flow, req_flow, res_flow)

    if raw_flow.request:
        print(format_request(raw_flow, req_flow, config))

    if raw_flow.response:
        print(format_response(raw_flow, res_flow))

    if raw_request_file is not None and raw_response_file is not None:
        print("\n# Raw Traces")
        print(f"Written raw request to {raw_request_file}")
        print(f"Written raw response to {raw_response_file}")


def _write_trace(raw_flow: http.HTTPFlow, req_flow: RequestFlow, res_flow: ResponseFlow) -> tuple[Path, Path]:
    now = datetime.now().isoformat()
    raw_request_file = Path(__file__).parent.parent / 'trace' / f"{now}-req.json"
    raw_response_file = Path(__file__).parent.parent / 'trace' / f"{now}-res.json"
    if req_flow.pretty:
        with open(raw_request_file, "w") as f:
            f.write(req_flow.pretty)
    elif raw_flow.request and raw_flow.request.text:
        print("Pretty request is missing")
        with open(raw_response_file, "w") as f:
            f.write(raw_flow.request.text)

    if res_flow.pretty:
        with open(raw_response_file, "w") as f:
            f.write(res_flow.pretty)
    elif raw_flow.response and raw_flow.response.text:
        print("Pretty response is missing")
        with open(raw_response_file, "w") as f:
            f.write(raw_flow.response.text)
    return raw_request_file, raw_response_file
