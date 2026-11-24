"""Teste rápido das credenciais MariTalk. Uso: python3 test/test_maritalk.py

Lê MARITALK_API_KEY, MARITALK_API_BASE e MARITALK_MODEL do ambiente.
Faz uma requisição de chat real. Exit 0 = chave válida, 1 = falhou, 2 = variáveis ausentes.
A chave nunca é impressa.
"""
import json
import os
import sys
from urllib import error, request


ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")


def load_env_file(path: str) -> None:
	"""Carrega KEY=VALUE do .env sem sobrescrever o que já está no ambiente."""
	if not os.path.isfile(path):
		return
	with open(path, encoding="utf-8") as fh:
		for line in fh:
			line = line.strip()
			if not line or line.startswith("#") or "=" not in line:
				continue
			key, value = line.split("=", 1)
			key = key.strip().removeprefix("export ").strip()
			value = value.strip().strip("'\"")
			os.environ.setdefault(key, value)


def check_credentials() -> tuple[int, str]:
	load_env_file(ENV_FILE)
	api_key = os.getenv("MARITALK_API_KEY")
	api_base = os.getenv("MARITALK_API_BASE")
	model = os.getenv("MARITALK_MODEL")

	if not api_key or not api_base or not model:
		return 2, "Variáveis ausentes: MARITALK_API_KEY, MARITALK_API_BASE, MARITALK_MODEL"

	url = api_base.rstrip("/") + "/chat/completions"
	payload = {
		"model": model,
		"messages": [{"role": "user", "content": "Responda apenas: ok"}],
		"max_tokens": 16,
		"temperature": 0,
	}
	req = request.Request(
		url,
		data=json.dumps(payload).encode("utf-8"),
		headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
		method="POST",
	)

	try:
		with request.urlopen(req, timeout=30) as resp:
			raw = resp.read().decode("utf-8", errors="replace")
	except error.HTTPError as exc:
		if exc.code in (401, 403):
			return 1, f"Credencial recusada pela MariTalk (HTTP {exc.code})."
		detail = exc.read().decode("utf-8", errors="replace")[:200]
		return 1, f"MariTalk respondeu HTTP {exc.code}: {detail}"
	except error.URLError as exc:
		return 1, f"Não foi possível conectar em {url}: {exc.reason}"

	try:
		body = json.loads(raw)
	except json.JSONDecodeError:
		return 1, "Resposta não é JSON válido."

	choices = body.get("choices") or []
	if not choices:
		return 1, "Resposta sem 'choices'."
	content = (choices[0].get("message") or {}).get("content", "")
	if not isinstance(content, str) or not content.strip():
		return 1, "Resposta sem conteúdo de texto."

	return 0, f"Chave válida. Modelo {model} respondeu: {content.strip()[:80]}"


def main() -> int:
	code, message = check_credentials()
	print(("OK    " if code == 0 else "FALHA ") + message)
	return code


if __name__ == "__main__":
	sys.exit(main())
