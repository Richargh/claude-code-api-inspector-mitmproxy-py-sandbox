from hidden.flows import parse_flow

def response(raw_flow) -> None:
    flow = parse_flow(raw_flow)

    if flow.request_error:
        print(f"Request Error: {raw_flow.request.text[:1000]}")
    elif flow.model:
        print(f"\nRequest:")
        print(f"  model: {flow.model}")
        print(f"  lastMessage: @{flow.last_message_role}: {flow.last_message_text}")

    if raw_flow.response:
        if flow.response_error:
            print(f"Response Error: {raw_flow.response.text[:1000]}")
        elif flow.response_text is not None:
            # SSE response
            print(f"\nResponse:")
            print(f"  model: {flow.response_model}")
            print(f"  text: {flow.response_text[:500]}")
        else:
            print(f"\nResponse:")
            print(f"  model: {flow.model}")

        print('=' * 60)
