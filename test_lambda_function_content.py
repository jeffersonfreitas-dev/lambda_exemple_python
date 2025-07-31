import json

import pytest
import responses
from unittest.mock import patch

from lambda_function_content import _get_token, lambda_function, _send_content

BASE_URL = "http://localhost:8080"
TOKEN_MOCK_RESPONSE = {"access_token": "eyJhbGciOiJIUzI1NiIsImt", "token_type": "Bearer", "expires_in": 1079}


@pytest.fixture
def mock_get_token():
    with patch("lambda_function._get_token") as mock:
        yield mock

@pytest.fixture
def mock_send_object():
    with patch("lambda_function._send_content") as mock:
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
    (None, "token", "Requisição recebida não pode ter o objeto nulo"),
    ("", "token", "String do objeto não pode ser vazio ou conter apenas espaços"),
    ("   ", "token", "String do objeto não pode ser vazio ou conter apenas espaços"),
    ({}, "token", "Objeto não pode ser vazio"),
    ([], "token", "Tipo de objeto inválido. Deve ser string ou dicionário"),
    (123, "token", "Tipo de objeto inválido. Deve ser string ou dicionário"),
    ({"test":"test"}, "token", "Campos obrigatórios 'name' não informado ou está vazio."),
    ('{"test":"test"}', "token", "Campos obrigatórios 'name' não informado ou está vazio."),
    ({"name":""}, "token", "Campos obrigatórios 'name' não informado ou está vazio."),
    ({"name":"correct"}, "token", "Campos obrigatórios 'file' não informado ou está vazio."),
    ({"name":"correct", "file": ""}, "token", "Campos obrigatórios 'file' não informado ou está vazio."),
    ("teste", "token", "String do objeto não pode ser vazio ou conter apenas espaços"),
])
def test_send_content_parameter_validation(content, token, expected_error):
    result = _send_content(content, token)

    assert expected_error == result["message"]
    assert result["statusCode"] == 400


@responses.activate
def test_send_content_success_dict():
    responses.add(responses.POST, f"{BASE_URL}", status=200)
    token = "eyJhbGciOiJIUzI1"
    body = {
        "name": "test_name",
        "file": "UEsDBBQAAAAIAJNN3lpGx01IlQ=="
    }
    result = _send_content(body, token)

    assert result == {"statusCode": 200, "message": "Registro criado com sucesso"}
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == f"{BASE_URL}/"
    assert responses.calls[0].request.headers["Authorization"] == f"Bearer {token}"

@responses.activate
def test_send_content_success_str():
    responses.add(responses.POST, f"{BASE_URL}", status=200)
    token = "eyJhbGciOiJIUzI1"
    body = json.dumps({
        "name": "test_name",
        "file": "UEsDBBQAAAAIAJNN3lpGx01IlQ=="
    })
    result = _send_content(body, token)

    assert result == {"statusCode": 200, "message": "Registro criado com sucesso"}
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == f"{BASE_URL}/"
    assert responses.calls[0].request.headers["Authorization"] == f"Bearer {token}"


@responses.activate
def test_send_content_error():
    token = "eyJhbGciOiJIUzI1"
    body = json.dumps({
        "name": "test_name",
        "file": "UEsDBBQAAAAIAJNN3lpGx01IlQ=="
    })
    status_code = 400
    error_respose = {"statusCode": status_code, "message": "Erro http"}
    responses.add(responses.POST, f"{BASE_URL}", status=status_code, json=error_respose)
    result = _send_content(body, token)

    assert result == error_respose
    assert len(responses.calls) == 1


def test_lambda_function_null_token(mock_get_token):
    mock_get_token.return_value = None
    event = [{"valid": "event"}]

    result = lambda_function(event, None)

    assert result["statusCode"] == 400
    assert "token não pode ser nulo" in result["message"]


def test_lambda_function_null_response(mock_get_token, mock_send_object):
    mock_get_token.return_value = {"access_token": "eyJhbGciOiJIUzI1"}
    mock_send_object.return_value = None
    event = [{"valid": "event"}]

    result = lambda_function(event, None)

    assert result["statusCode"] == 400
    assert "problema no envio" in result["message"]


def test_lambda_function_success(mock_get_token, mock_send_object):
    mock_get_token.return_value = {"access_token": "eyJhbGciOiJIUzI1"}
    mock_send_object.return_value = {"statusCode": 202, "message": "Registro criado com sucesso"}
    event = [{"valid": "event"}]

    result = lambda_function(event, None)

    assert result["statusCode"] == 202
    assert "sucesso" in result["message"]