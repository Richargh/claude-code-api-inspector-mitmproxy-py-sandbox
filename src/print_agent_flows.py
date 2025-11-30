import re
from datetime import datetime
from pathlib import Path

from mitmproxy import http

from internal.flow_config import FlowConfig
from internal.format_request import format_request
from internal.format_response import format_response
from internal.parse_flows import RequestFlow, ResponseFlow, parse_flow

_ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;]*m')

_DEFAULT_CONFIG = FlowConfig()


def response(raw_flow: http.HTTPFlow, config: FlowConfig = _DEFAULT_CONFIG) -> None:
    req_flow, res_flow = parse_flow(raw_flow)
    raw_request_file = None
    raw_response_file = None
    format_file = None
    if config.write_trace:
        raw_request_file, raw_response_file, format_file = _write_trace(raw_flow, req_flow, res_flow, config)

    if raw_flow.request:
        print(format_request(raw_flow, req_flow, config))

    if raw_flow.response:
        print(format_response(raw_flow, res_flow))

    if raw_request_file is not None and raw_response_file is not None and format_file is not None:
        print("\n# Raw Traces")
        print(f"Written raw request to {raw_request_file}")
        print(f"Written raw response to {raw_response_file}")
        print(f"Written formatted output to {format_file}")


def _write_trace(
        raw_flow: http.HTTPFlow, req_flow: RequestFlow, res_flow: ResponseFlow, config: FlowConfig
) -> tuple[Path, Path, Path]:
    now = datetime.now().isoformat()
    trace_dir = Path(__file__).parent.parent / 'trace'
    raw_request_file = trace_dir / f"{now}-req.json"
    raw_response_file = trace_dir / f"{now}-res.json"
    format_file = trace_dir / f"{now}-format.txt"

    if req_flow.pretty:
        with open(raw_request_file, "w") as f:
            f.write(req_flow.pretty)
    elif raw_flow.request and raw_flow.request.text:
        print("Pretty request is missing")
        with open(raw_request_file, "w") as f:
            f.write(raw_flow.request.text)

    if res_flow.pretty:
        with open(raw_response_file, "w") as f:
            f.write(res_flow.pretty)
    elif raw_flow.response and raw_flow.response.text:
        print("Pretty response is missing")
        with open(raw_response_file, "w") as f:
            f.write(raw_flow.response.text)

    # Write formatted output (strip ANSI color codes for file)
    formatted_output = []
    if raw_flow.request:
        formatted_output.append(format_request(raw_flow, req_flow, config))
    if raw_flow.response:
        formatted_output.append(format_response(raw_flow, res_flow))
    plain_text = _ANSI_ESCAPE_PATTERN.sub('', '\n'.join(formatted_output))
    with open(format_file, "w") as f:
        f.write(plain_text)

    return raw_request_file, raw_response_file, format_file
