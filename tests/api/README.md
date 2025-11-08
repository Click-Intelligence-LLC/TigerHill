# HTTP API Testing

Test an HTTP API endpoint with request/response validation

## Generated Configuration

- **Agent Name**: `user-api-test`
- **API URL**: `http://localhost:3000/api/users`
- **HTTP Method**: `GET`
- **Expected Status**: `200`
- **Validation**: Enabled

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the test:

```bash
pytest test_user-api-test.py -v
```

View test traces:

```bash
# The test automatically records traces to a temporary directory
# For persistent traces, modify the trace_store fixture to use a fixed path
```

## Customization

You can modify the generated test script to add:

- **Custom Headers**: Add headers to the request
- **Authentication**: Add authentication (Bearer token, Basic auth, etc.)
- **Query Parameters**: Add URL query parameters
- **Response Schema Validation**: Use `assert_response_json_schema`
- **Multiple Test Cases**: Add more test methods

### Example: Adding Authentication

```python
def test_user_api_test_with_auth(self, adapter, trace_store):
    adapter.set_header("Authorization", "Bearer YOUR_TOKEN")
    # ... rest of test
```

### Example: Adding Query Parameters

```python
response = adapter.execute(
    trace_id=trace_id,
    method="GET",
    endpoint="/",
    params={"key": "value"}
)
```

## Documentation

For more information, see:
- [TigerHill Documentation](https://github.com/yourusername/tigerhill)
- [HTTP Adapter Reference](https://github.com/yourusername/tigerhill/docs/adapters/http.md)
- [Assertions Reference](https://github.com/yourusername/tigerhill/docs/assertions.md)