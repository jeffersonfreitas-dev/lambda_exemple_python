import logging
from functools import wraps

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
def _delete_object(resource: dict, token: str) -> dict:
    if not resource:
        return _build_response(400, "Código do recurso não pode ser nulo")

    if not isinstance(resource, dict):
        return _build_response(400, "Tipo inválido. Deve ser um dicionário")

    if "id" not in resource or not resource.get("id"):
        return _build_response(400, "Código do recurso é obrigatório para exclusão")

    request_header = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    resource_id = resource.get("id")
    response = requests.delete(f"{BASE_URL}/{resource_id}", headers=request_header)
    response.raise_for_status()
    return _build_response(200, f"Registro {resource_id} excluído com sucesso")



def lambda_function(event, context):
    try:
        token = _get_token(CLIENT_ID, SECRET_ID, ACCOUNT_ID)
        if not token:
            raise ValueError("O token não pode ser nulo ou vazio")

        delete_result = _delete_object(event, token["access_token"])
        if not delete_result:
            raise ValueError("Houve um problema no envio da requisição")

        return delete_result

    except ValueError as errv:
        logging.error(f"Erro de validação: {errv}")
        return _build_response(400, str(errv))

    except Exception as err:
        logging.error(f"Erro ao tentar realizar a requisição: {str(err)}")
        return _build_response(500, "Ocorreu um erro genérico na requisição")


