from flask import Flask, request

from functions.main import hello


def test_hello_returns_message():
    app = Flask(__name__)
    with app.test_request_context("/"):
        response = hello(request)
    assert response.get_data(as_text=True) == "CARLLM Functions online."
