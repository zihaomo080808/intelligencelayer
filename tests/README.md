# Testing the Twilio Integration

This directory contains tests and tools for testing the Twilio SMS integration.

## Running the Automated Tests

To run the automated tests, make sure you have the test dependencies installed:

```bash
pip install pytest pytest-asyncio httpx
```

Then run the tests with:

```bash
pytest tests/test_twilio_handler.py -v
```

The tests use mocking to avoid making actual database or API calls, so you don't need a running database or Twilio credentials to run them.

## Manual Testing

For manual testing, you can use the `simulate_twilio_request.py` script to send simulated Twilio webhook requests to your local server:

1. Start your FastAPI server:
   ```bash
   uvicorn api.main:app --reload
   ```

2. In another terminal, run the simulator:
   ```bash
   python tests/simulate_twilio_request.py
   ```

3. Follow the interactive prompts to send different types of test messages.

This allows you to test the full flow of SMS handling without needing to expose your local server to the internet or set up a Twilio phone number.

## Test Database

The tests are configured to use a test database instead of your production database. You may need to adjust the database connection string in `conftest.py` to match your test environment.

## Note on Twilio Validation

When testing with the simulator, request validation is bypassed because the DEBUG flag is set to True. In production, make sure DEBUG is set to False to enforce Twilio request validation. 