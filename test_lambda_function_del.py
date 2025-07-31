import json

import pytest
import responses
from unittest.mock import patch

from lambda_function_del import _get_token, lambda_function, _delete_object

BASE_URL = "http://localhost:8080"
TOKEN_MOCK_RESPONSE = {"access_token": "eyJhbGciOiJIUzI1NiIsImt", "token_type": "Bearer", "expires_in": 1079}


@pytest.fixture
def mock_get_token():
    with patch("lambda_function._get_token") as mock:
        yield mock

@pytest.fixture
def mock_delete_object():
    with patch("lambda_function._delete_object") as mock:
        yield mock

@responses.activate
def test_get_token_success():
    responses.add(responses.POST, f"{BASE_URL}/token", json=TOKEN_MOCK_RESPONSE, status=200)
    result = _get_token("123", "2456", "789")

    assert result == TOKEN_MOCK_RESPONSE
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == f"{BASE_URL}/token"
    assert responses.calls[0].request.headers["Content-Type"] == "application/json"


@responses.activate
def test_get_token_error_pass_invalid_credentials():
    status_code = 401
    token_error_respose = {"statusCode": status_code, "message": "Erro http"}
    responses.add(responses.POST, f"{BASE_URL}/token", status=status_code, json=token_error_respose)
    result = _get_token("123", "456", "789")

    assert result == token_error_respose
    assert len(responses.calls) == 1


@pytest.mark.parametrize("client_id, client_secret, account_id, expected_error", [
    # None
    (None, "secret", "account", "client_id não pode ser nulo ou vazio"),
    ("id", None, "account", "client_secret não pode ser nulo ou vazio"),
    ("id", "secret", None, "account_id não pode ser nulo ou vazio"),

    # Empy
    ("", "secret", "account", "client_id não pode ser nulo ou vazio"),
    ("id", "", "account", "client_secret não pode ser nulo ou vazio"),
    ("id", "secret", "", "account_id não pode ser nulo ou vazio"),

    # Whitespace
    ("   ", "secret", "account", "client_id não pode ser nulo ou vazio"),
    ("id", "    ", "account", "client_secret não pode ser nulo ou vazio"),
    ("id", "secret", "   ", "account_id não pode ser nulo ou vazio"),
])
def test_get_token_parameter_validation(client_id, client_secret, account_id, expected_error):
    result = _get_token(client_id, client_secret, account_id)

    assert expected_error == result["message"]
    assert result["statusCode"] == 400


@pytest.mark.parametrize("content, token, expected_error", [
    (None, "token", "Código do recurso não pode ser nulo"),
    ("", "token", "Código do recurso não pode ser nulo"),
    ("   ", "token", "Tipo inválido. Deve ser um dicionário"),
    ({}, "token", "Código do recurso não pode ser nulo"),
    ([], "token", "Código do recurso não pode ser nulo"),
    (123, "token", "Tipo inválido. Deve ser um dicionário"),
    ({"test":"test"}, "token", "Código do recurso é obrigatório para exclusão"),
    ({"id":""}, "token", "Código do recurso é obrigatório para exclusão"),
])
def test_delete_object_parameter_validation(content, token, expected_error):
    result = _delete_object(content, token)

    assert expected_error == result["message"]
    assert result["statusCode"] == 400


@responses.activate
def test_delete_object_success_dict():
    codigo = 123
    responses.add(responses.DELETE, f"{BASE_URL}/{codigo}", status=200)
    token = "eyJhbGciOiJIUzI1"
    body = {"id": codigo}
    result = _delete_object(body, token)

    assert result == {"statusCode": 200, "message": f"Registro {codigo} excluído com sucesso"}
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == f"{BASE_URL}/{codigo}"
    assert responses.calls[0].request.headers["Authorization"] == f"Bearer {token}"


@responses.activate
def test_delete_object_error():
    codigo = 123
    token = "eyJhbGciOiJIUzI1"
    body = {"id": codigo}
    status_code = 400
    error_respose = {"statusCode": status_code, "message": "Erro http"}
    responses.add(responses.DELETE, f"{BASE_URL}/{codigo}", status=status_code, json=error_respose)
    result = _delete_object(body, token)

    assert result == error_respose
    assert len(responses.calls) == 1


def test_lambda_function_null_token(mock_get_token):
    mock_get_token.return_value = None
    event = [{"valid": "event"}]

    result = lambda_function(event, None)

    assert result["statusCode"] == 400
    assert "token não pode ser nulo" in result["message"]


def test_lambda_function_null_response(mock_get_token, mock_delete_object):
    mock_get_token.return_value = {"access_token": "eyJhbGciOiJIUzI1"}
    mock_delete_object.return_value = None
    event = [{"valid": "event"}]

    result = lambda_function(event, None)

    assert result["statusCode"] == 400
    assert "problema no envio" in result["message"]


def test_lambda_function_success(mock_get_token, mock_delete_object):
    mock_get_token.return_value = {"access_token": "eyJhbGciOiJIUzI1"}
    mock_delete_object.return_value = {"statusCode": 202, "message": "Registro criado com sucesso"}
    event = [{"valid": "event"}]

    result = lambda_function(event, None)

    assert result["statusCode"] == 202
    assert "sucesso" in result["message"]