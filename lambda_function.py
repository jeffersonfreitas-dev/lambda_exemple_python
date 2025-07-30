import logging
from functools import wraps

import requests

BASE_URL = "http://localhost:8080"
CLIENT_ID = ""
SECRET_ID = ""
ACCOUNT_ID = ""

def handle_http_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as errh:
            exp_code = errh.response.status_code
            logging.error(f"Erro Http code {exp_code} : {str(errh)}")
            return build_response(errh.response.status_code, "Erro http")

        except requests.exceptions.ConnectionError as errc:
            logging.error(f"Erro Conexão: {str(errc)}")
            return build_response(errc.response.status_code, "Erro Conexão")

        except requests.exceptions.Timeout as errt:
            logging.error(f"Erro Timeout: {str(errt)}")
            return build_response(errt.response.status_code, "Erro Timeout")

        except requests.exceptions.RequestException as err:
            logging.error(f"Erro Inesperado: {str(err)}")
            return build_response(err.response.status_code, "Erro inesperado")
    return wrapper


def build_response(status_code: int, body_message: str) -> dict:
    return {
        "statusCode": status_code,
        "message": body_message
    }


@handle_http_errors
def get_token(client_id: str, client_secret: str, account_id: str) -> dict:
    if not client_id or client_id.isspace():
        return build_response(400, "client_id não pode ser nulo ou vazio")

    if not client_secret or client_secret.isspace():
        return build_response(400, "client_secret não pode ser nulo ou vazio")

    if not account_id or account_id.isspace():
        return build_response(400, "account_id não pode ser nulo ou vazio")

    body = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "account_id": account_id
    }

    response = requests.post(f"{BASE_URL}/token", body, headers={"Content-Type": "application/json"})
    response.raise_for_status()
    return response.json()



@handle_http_errors
def send_object(request_obj: str | list | dict, token: str) -> dict:
    if request_obj is None:
        return build_response(400, "Requisição recebida não pode ter o objeto nulo")

    if isinstance(request_obj, str):
        if not request_obj.strip():
            return build_response(400, "String do objeto não pode ser vazio ou conter apenas espaços")
    elif isinstance(request_obj, list) or isinstance(request_obj, dict):
        if not request_obj:
            return build_response(400, "Objeto não pode ser vazio")
    else:
        return build_response(400, "Tipo de objeto inválido. Deve ser string, lista ou dicionário")

    request_header = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(f"{BASE_URL}", request_obj, headers=request_header)
    response.raise_for_status()
    return build_response(202, "Registro criado com sucesso")



def lambda_function(event, context):
    try:
        token = get_token(CLIENT_ID, SECRET_ID, ACCOUNT_ID)
        if not token:
            raise ValueError("O token não pode ser nulo ou vazio")

        send_result = send_object(event, token["access_token"])
        if not send_result:
            raise ValueError("Houve um problema no envio da requisição")

        return send_result

    except ValueError as errv:
        logging.error(f"Erro de validação: {errv}")
        return build_response(400, str(errv))

    except Exception as err:
        logging.error(f"Erro ao tentar realizar a requisição: {str(err)}")
        return build_response(500, "Ocorreu um erro genérico na requisição")


