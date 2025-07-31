import json
import logging
from functools import wraps
from typing import Optional

import requests

BASE_URL = "http://localhost:8080"
CLIENT_ID = ""
SECRET_ID = ""
ACCOUNT_ID = ""

def _handle_http_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as errh:
            exp_code = errh.response.status_code
            logging.error(f"Erro Http code {exp_code} : {str(errh)}")
            return _build_response(errh.response.status_code, "Erro http")

        except requests.exceptions.ConnectionError as errc:
            logging.error(f"Erro Conexão: {str(errc)}")
            return _build_response(errc.response.status_code, "Erro Conexão")

        except requests.exceptions.Timeout as errt:
            logging.error(f"Erro Timeout: {str(errt)}")
            return _build_response(errt.response.status_code, "Erro Timeout")

        except requests.exceptions.RequestException as err:
            logging.error(f"Erro Inesperado: {str(err)}")
            return _build_response(err.response.status_code, "Erro inesperado")
    return wrapper


def _build_response(status_code: int, body_message: str) -> dict:
    return {
        "statusCode": status_code,
        "message": body_message
    }


@_handle_http_errors
def _get_token(client_id: str, client_secret: str, account_id: str) -> dict:
    if not client_id or client_id.isspace():
        return _build_response(400, "client_id não pode ser nulo ou vazio")

    if not client_secret or client_secret.isspace():
        return _build_response(400, "client_secret não pode ser nulo ou vazio")

    if not account_id or account_id.isspace():
        return _build_response(400, "account_id não pode ser nulo ou vazio")

    body = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "account_id": account_id
    }

    response = requests.post(f"{BASE_URL}/token", body, headers={"Content-Type": "application/json"})
    response.raise_for_status()
    return response.json()



@_handle_http_errors
def _send_content(content: str | dict, token: str) -> dict:
    try:
        request_body = _validate_content(content)

        request_header = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.post(f"{BASE_URL}", request_body, headers=request_header)
        response.raise_for_status()
        # todo: Enviar o id do objeto para o SQS

        return _build_response(200, "Registro criado com sucesso")
    except ValueError as errv:
        return _build_response(400, str(errv))


def _validate_content(content: str | dict) -> Optional[dict]:
    if content is None:
        raise ValueError("Requisição recebida não pode ter o objeto nulo")

    if isinstance(content, str):
        try:
            content_dict = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("String do objeto não pode ser vazio ou conter apenas espaços")

    elif isinstance(content, dict):
        if not content:
            raise ValueError("Objeto não pode ser vazio")
        else:
            content_dict = content
    else:
        raise ValueError("Tipo de objeto inválido. Deve ser string ou dicionário")

    if "name" not in content_dict or not content_dict.get("name"):
        raise ValueError("Campos obrigatórios 'name' não informado ou está vazio.")

    if "file" not in content_dict or not content_dict.get("file"):
        raise ValueError("Campos obrigatórios 'file' não informado ou está vazio.")

    return content_dict


def lambda_function(event, context):
    try:
        token = _get_token(CLIENT_ID, SECRET_ID, ACCOUNT_ID)
        if not token:
            raise ValueError("O token não pode ser nulo ou vazio")

        send_result = _send_content(event, token["access_token"])
        if not send_result:
            raise ValueError("Houve um problema no envio da requisição")

        return send_result

    except ValueError as errv:
        logging.error(f"Erro de validação: {errv}")
        return _build_response(400, str(errv))

    except Exception as err:
        logging.error(f"Erro ao tentar realizar a requisição: {str(err)}")
        return _build_response(500, "Ocorreu um erro genérico na requisição")


