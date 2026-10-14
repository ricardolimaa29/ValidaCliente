"""Integração assíncrona Plexi/CENPROT. Não contém segredos nem simula resultados."""
import re
import requests

BASE = "https://api.plexi.com.br"
ENDPOINTS = {
    "nacional": "/api/maestro/cenprot/consulta-protesto",
    "sp": "/api/maestro/cenprot-sp/consulta-protesto",
}

class PlexiError(Exception):
    pass

def request_id_valido(request_id):
    return bool(re.fullmatch(r"[a-fA-F0-9-]{36}", str(request_id)))

def solicitar(cnpj, escopo, token, certificate=None, credential=None):
    if escopo not in ENDPOINTS:
        raise PlexiError("Escopo desconhecido")
    if not token:
        raise PlexiError("Token Plexi não configurado")
    if escopo == "sp" and not certificate:
        raise PlexiError("CENPROT SP exige certificado cadastrado e habilitado")
    if escopo == "nacional" and bool(certificate) == bool(credential):
        raise PlexiError("Nacional exige exatamente um: certificate OU credential")
    body = {"cpfCnpj": cnpj}
    if certificate:
        body["certificate"] = certificate
    else:
        body["credential"] = credential
    try:
        r = requests.post(BASE + ENDPOINTS[escopo], json=body,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30)
        if r.status_code != 201:
            raise PlexiError(f"Falha ao solicitar {escopo}: HTTP {r.status_code}; consulte permissões, créditos e configuração.")
        data = r.json()
        rid = data.get("requestId")
        if not request_id_valido(rid):
            raise PlexiError("Plexi não retornou requestId válido")
        return rid
    except (requests.RequestException, ValueError) as exc:
        raise PlexiError(f"Falha de comunicação com Plexi: {type(exc).__name__}") from exc

def resultado(request_id, token):
    if not token or not request_id_valido(request_id):
        raise PlexiError("Token ou requestId inválido")
    try:
        r = requests.get(f"{BASE}/api/maestro/result/{request_id}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=30)
        if r.status_code == 202:
            return {"estado": "processando", "dados": None}
        if r.status_code != 200:
            raise PlexiError(f"Consulta de resultado: HTTP {r.status_code}")
        data = r.json()
        if not isinstance(data, dict):
            raise PlexiError("Resposta inesperada da Plexi")
        status = str(data.get("status", "")).lower()
        if data.get("error") or status == "erro":
            return {"estado": "erro", "dados": data}
        if status in ("positiva", "positivo", "negativa", "negativo"):
            return {"estado": "concluido", "dados": data}
        return {"estado": "inconclusivo", "dados": data}
    except (requests.RequestException, ValueError) as exc:
        raise PlexiError(f"Falha de comunicação com Plexi: {type(exc).__name__}") from exc
