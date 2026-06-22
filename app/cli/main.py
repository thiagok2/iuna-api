"""
CLI para gerenciamento do IUNA API.

Uso: python -m app.cli.main <command>
"""

import json
from pathlib import Path

import typer
from elasticsearch import Elasticsearch

from app.config import settings

app = typer.Typer(
    name="iuna",
    help="CLI de gerenciamento do IUNA API — índices, ingestão e utilitários.",
)

# ---------------------------------------------------------------------------
# Mapping: arquivo JSON → nome base do índice
# ---------------------------------------------------------------------------
INDEX_MAPPINGS: list[tuple[str, str]] = [
    ("elastic/documentos_ifal_v2_mapping.json", "documentos_ifal_v2"),
    ("elastic/documentos_ifal_v2_mapping_chunks.json", "documentos_ifal_v2_chunks"),
    ("elastic/artefatos_mapping.json", "artefatos"),
    ("elastic/artefatos_chunks_mapping.json", "artefatos_chunks"),
    ("elastic/chat_sessions_mapping.json", "chat_sessions"),
]


def _get_es_client() -> Elasticsearch:
    """Cria um cliente Elasticsearch síncrono a partir das settings."""
    if not settings.ELASTICSEARCH_HOSTS:
        typer.echo("❌ ELASTICSEARCH_HOSTS não configurado. Verifique .env")
        raise typer.Exit(code=1)

    hosts = [h.strip() for h in settings.ELASTICSEARCH_HOSTS.split(",")]

    kwargs: dict = {
        "hosts": hosts,
        "verify_certs": False,
        "ssl_show_warn": False,
    }

    if settings.ELASTICSEARCH_USER and settings.ELASTICSEARCH_PASSWORD:
        kwargs["basic_auth"] = (
            settings.ELASTICSEARCH_USER,
            settings.ELASTICSEARCH_PASSWORD,
        )

    return Elasticsearch(**kwargs)


def _extract_body(raw: dict) -> dict:
    """
    Extrai o body para criação do índice a partir do JSON com wrapper.

    O arquivo tem formato:
        {"index_name": {"mappings": {...}, "_meta": {...}}}

    Retorna: {"mappings": {...}} com _meta dentro de mappings se necessário.
    """
    # Pega o conteúdo dentro da primeira (única) chave wrapper
    wrapper_key = next(iter(raw))
    inner = raw[wrapper_key]

    body: dict = {}

    # Settings (se existir)
    if "settings" in inner:
        body["settings"] = inner["settings"]

    # Mappings
    if "mappings" in inner:
        mappings = inner["mappings"].copy()
        # Se _meta está no nível do wrapper (fora de mappings), move para dentro
        if "_meta" in inner and "_meta" not in mappings:
            mappings["_meta"] = inner["_meta"]
        body["mappings"] = mappings
    elif "_meta" in inner:
        # Caso improvável: só _meta sem mappings
        body["mappings"] = {"_meta": inner["_meta"]}

    return body


# ---------------------------------------------------------------------------
# Comando: setup-indices
# ---------------------------------------------------------------------------
@app.command("setup-indices")
def setup_indices(
    suffix: str = typer.Option("", help="Sufixo para anexar aos nomes dos índices (ex: _test)."),
    recreate: bool = typer.Option(
        False, help="Apaga e recria índices existentes. PERIGOSO — nunca use sem intenção!"
    ),
) -> None:
    """Cria os índices do Elasticsearch a partir dos arquivos de mapeamento."""

    if recreate:
        typer.echo(
            "⚠️  ATENÇÃO: --recreate vai APAGAR e RECRIAR os índices. Tem certeza? (y/N)"
        )
        confirm = input().strip().lower()
        if confirm != "y":
            typer.echo("Operação cancelada.")
            raise typer.Exit()

    es = _get_es_client()

    # Verifica conexão
    try:
        if not es.ping():
            typer.echo("❌ Não foi possível conectar ao Elasticsearch.")
            raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"❌ Erro ao conectar ao Elasticsearch: {e}")
        raise typer.Exit(code=1)

    typer.echo("🔌 Conectado ao Elasticsearch\n")

    project_root = Path(__file__).resolve().parent.parent.parent

    for mapping_file, base_name in INDEX_MAPPINGS:
        index_name = f"{base_name}{suffix}"
        file_path = project_root / mapping_file

        if not file_path.exists():
            typer.echo(f"❌ {index_name} — arquivo não encontrado: {mapping_file}")
            continue

        # Lê e processa o JSON
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        body = _extract_body(raw)

        # Verifica se o índice já existe
        exists = es.indices.exists(index=index_name)

        if exists and not recreate:
            typer.echo(f"⏭  {index_name} — Already exists")
            continue

        if exists and recreate:
            es.indices.delete(index=index_name)
            es.indices.create(index=index_name, body=body)
            typer.echo(f"🔄 {index_name} — Recreated")
            continue

        # Índice não existe: cria
        es.indices.create(index=index_name, body=body)
        typer.echo(f"✅ {index_name} — Created")

    typer.echo("\n🏁 setup-indices finalizado.")
    es.close()


# ---------------------------------------------------------------------------
# Stub commands
# ---------------------------------------------------------------------------
@app.command()
def enrich() -> None:
    """Enriquece documentos com IA (resumo, entidades, keywords)."""
    typer.echo("Not implemented yet")


@app.command()
def ingest() -> None:
    """Ingere documentos no Elasticsearch."""
    typer.echo("Not implemented yet")


@app.command()
def delete() -> None:
    """Apaga documentos ou índices."""
    typer.echo("Not implemented yet")


@app.command()
def stats() -> None:
    """Exibe estatísticas dos índices."""
    typer.echo("Not implemented yet")


# ---------------------------------------------------------------------------
# Entrypoint: python -m app.cli.main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app()
