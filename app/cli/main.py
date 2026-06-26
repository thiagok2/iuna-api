"""
CLI para gerenciamento do IUNA API.

Uso: python -m app.cli.main <command>
"""

import asyncio
import json
import logging
from pathlib import Path

import typer
from elasticsearch import Elasticsearch

from app.config import settings

app = typer.Typer(
    name="iuna",
    help="CLI de gerenciamento do IUNA API — índices, ingestão e utilitários.",
)

logger = logging.getLogger(__name__)

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
# Comando: ingest
# ---------------------------------------------------------------------------
@app.command()
def ingest(
    source_type: str = typer.Option(..., "--source-type", help="documentos_ifal_v2 | artefatos"),
    directory: str = typer.Option(..., "--directory", help="Diretório com PDFs"),
    force: bool = typer.Option(False, "--force", help="Sobrescrever existentes"),
    enrich: bool = typer.Option(False, "--enrich", help="Enriquecer após indexar (não implementado)"),
    concurrency: int = typer.Option(3, "--concurrency", help="Concorrência máxima"),
) -> None:
    """Indexa PDFs de um diretório no Elasticsearch."""
    asyncio.run(_run_ingest(source_type, directory, force, enrich, concurrency))


async def _run_ingest(
    source_type: str, directory: str, force: bool, enrich: bool, concurrency: int
) -> None:
    """Core async logic for the ingest command."""
    from app.clients.es_client import es_client
    from app.services.artefatos_crud import ArtefatosCrudService
    from app.services.documentos_crud import DocumentosCrudService

    # Validate source type
    valid_types = ("documentos_ifal_v2", "artefatos")
    if source_type not in valid_types:
        typer.echo(f"❌ source-type inválido: {source_type}. Use: {', '.join(valid_types)}")
        raise typer.Exit(code=1)

    # Validate directory
    dir_path = Path(directory)
    if not dir_path.is_dir():
        typer.echo(f"❌ Diretório não encontrado: {directory}")
        raise typer.Exit(code=1)

    # Find all PDF files
    pdf_files = sorted(dir_path.glob("*.pdf"))
    if not pdf_files:
        typer.echo(f"⚠️  Nenhum arquivo PDF encontrado em: {directory}")
        raise typer.Exit(code=0)

    typer.echo(f"📂 Encontrados {len(pdf_files)} arquivos PDF em: {directory}")
    typer.echo(f"📌 Tipo: {source_type} | Force: {force} | Concurrency: {concurrency}")
    typer.echo("")

    # Connect to ES
    try:
        await es_client.connect()
    except Exception as exc:
        typer.echo(f"❌ Erro ao conectar ao Elasticsearch: {exc}")
        raise typer.Exit(code=1)

    # Pick the right service
    if source_type == "documentos_ifal_v2":
        service = DocumentosCrudService(es_client)
    else:
        service = ArtefatosCrudService(es_client)

    # Process files with concurrency control
    semaphore = asyncio.Semaphore(concurrency)
    success_count = 0
    error_count = 0
    total = len(pdf_files)

    async def _process_file(idx: int, pdf_path: Path) -> bool:
        nonlocal success_count, error_count
        async with semaphore:
            filename = pdf_path.name
            try:
                file_content = pdf_path.read_bytes()
                metadata = {"titulo": pdf_path.stem.replace("_", " ").title()}

                if source_type == "artefatos":
                    metadata["uploaded_by"] = "cli-ingest"

                await service.upload(file_content, filename, metadata, force=force)
                success_count += 1
                typer.echo(f"  ✅ [{idx}/{total}] {filename}")
                return True
            except Exception as exc:
                error_count += 1
                typer.echo(f"  ❌ [{idx}/{total}] {filename} — {exc}")
                return False

    # Create tasks
    tasks = [_process_file(i + 1, pdf) for i, pdf in enumerate(pdf_files)]
    await asyncio.gather(*tasks)

    # Cleanup
    await es_client.close()

    # Summary
    typer.echo("")
    typer.echo(f"🏁 Ingestão finalizada: {success_count} sucesso, {error_count} erro(s)")

    if enrich and success_count > 0:
        typer.echo("\n🧠 Iniciando enriquecimento dos documentos indexados...")
        await _run_enrich(
            source_type=source_type,
            ids_str=None,
            directory=directory,
            ops={"entities", "keywords", "summary", "vectorization", "chunking"},
            force=force,
            skip_existing=False,
            concurrency=concurrency,
        )


# ---------------------------------------------------------------------------
# Comando: enrich
# ---------------------------------------------------------------------------
@app.command()
def enrich(
    source_type: str = typer.Option(..., "--source-type", help="documentos_ifal_v2 | artefatos"),
    ids: str = typer.Option(None, "--ids", help="IDs separados por vírgula"),
    count: int = typer.Option(None, "--count", help="Busca N docs não-enriquecidos do ES automaticamente"),
    directory: str = typer.Option(None, "--directory", help="Diretório com PDFs (resolve por filename)"),
    from_es: bool = typer.Option(False, "--from-es", help="Varre o índice ES inteiro paginado via scroll"),
    batch_size: int = typer.Option(50, "--batch-size", help="Docs por lote no modo --from-es (default 50)"),
    summarize: bool = typer.Option(False, "--summarize", help="Gerar resumo"),
    vectorize: bool = typer.Option(False, "--vectorize", help="Gerar embedding"),
    entities: bool = typer.Option(False, "--entities", help="Extrair entidades"),
    keywords: bool = typer.Option(False, "--keywords", help="Extrair keywords"),
    chunk: bool = typer.Option(False, "--chunk", help="Gerar chunks"),
    enrich_all: bool = typer.Option(False, "--enrich", help="Executar todas as operações"),
    force: bool = typer.Option(False, "--force", help="Re-enriquecer mesmo se já existir"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip-existing", help="Pular docs já enriquecidos (default: True)"),
    concurrency: int = typer.Option(3, "--concurrency", help="Concorrência máxima"),
) -> None:
    """Enriquece documentos com IA (resumo, entidades, keywords, embedding, chunks)."""
    modes = sum([bool(ids), bool(count), bool(directory), from_es])
    if modes == 0:
        typer.echo("❌ Forneça um modo: --count, --ids, --directory ou --from-es")
        raise typer.Exit(code=1)
    if modes > 1:
        typer.echo("❌ Use apenas um modo por vez: --count, --ids, --directory ou --from-es")
        raise typer.Exit(code=1)

    ops: set[str] = set()
    if enrich_all:
        ops = {"entities", "keywords", "summary", "vectorization", "chunking"}
    else:
        if summarize:
            ops.add("summary")
        if vectorize:
            ops.add("vectorization")
        if entities:
            ops.add("entities")
        if keywords:
            ops.add("keywords")
        if chunk:
            ops.add("chunking")

    if not ops:
        typer.echo("⚠️  Nenhuma operação selecionada. Use --enrich ou flags específicas (--summarize, --entities, etc.)")
        raise typer.Exit(code=1)

    if from_es:
        asyncio.run(_run_enrich_from_es(source_type, ops, batch_size, force, skip_existing, concurrency))
    else:
        asyncio.run(_run_enrich(source_type, ids, directory, ops, force, skip_existing, concurrency, count))


async def _run_enrich(
    source_type: str,
    ids_str: str | None,
    directory: str | None,
    ops: set[str],
    force: bool,
    skip_existing: bool,
    concurrency: int,
    count: int | None = None,
) -> None:
    from app.clients.es_client import es_client
    from app.providers.factory import get_embedding_provider, get_llm_provider
    from app.services.enrichment import EnrichmentService

    valid_types = ("documentos_ifal_v2", "artefatos")
    if source_type not in valid_types:
        typer.echo(f"❌ source-type inválido: {source_type}. Use: {', '.join(valid_types)}")
        raise typer.Exit(code=1)

    try:
        await es_client.connect()
    except Exception as exc:
        typer.echo(f"❌ Erro ao conectar ao Elasticsearch: {exc}")
        raise typer.Exit(code=1)

    is_artefatos = source_type == "artefatos"
    index = settings.index_artefatos if is_artefatos else settings.index_documentos_ifal_v2
    chunks_index = settings.index_artefatos_chunks if is_artefatos else settings.index_documentos_ifal_v2_chunks
    root = "artefato" if is_artefatos else "ato"

    svc = EnrichmentService(es_client, get_llm_provider(), get_embedding_provider())

    # Resolve IDs
    doc_ids: list[str] = []

    if count:
        # determina o campo de skip pela primeira operação de geração presente
        skip_field = next(
            (f for op, f in [
                ("entities", f"{root}.entidades_at"),
                ("keywords", f"{root}.keywords_at"),
                ("summary", f"{root}.resumo_at"),
                ("vectorization", f"{root}.embedding_vector_at"),
                ("chunking", f"{root}.chunking_at"),
            ] if op in ops),
            f"{root}.entidades_at",
        )
        must_not: list[dict] = [{"bool": {"must_not": [{"wildcard": {"attachment.content": "*"}}]}}]
        if skip_existing and not force:
            must_not.append({"exists": {"field": skip_field}})
        resp = await es_client.search(
            index=index,
            body={"query": {"bool": {"must_not": must_not}}, "_source": False, "size": count},
        )
        doc_ids = [h["_id"] for h in resp.get("hits", {}).get("hits", [])]
        if not doc_ids:
            typer.echo("⚠️  Nenhum documento pendente encontrado.")
            await es_client.close()
            return
        typer.echo(f"📌 --count {count}: {len(doc_ids)} doc(s) encontrado(s) via ES")
    elif ids_str:
        doc_ids = [i.strip() for i in ids_str.split(",") if i.strip()]
    elif directory:
        dir_path = Path(directory)
        if not dir_path.is_dir():
            typer.echo(f"❌ Diretório não encontrado: {directory}")
            await es_client.close()
            raise typer.Exit(code=1)
        pdf_files = sorted(dir_path.glob("*.pdf"))
        if not pdf_files:
            typer.echo(f"⚠️  Nenhum arquivo PDF encontrado em: {directory}")
            await es_client.close()
            raise typer.Exit(code=0)
        for pdf in pdf_files:
            result = await es_client.search(
                index=index,
                body={"query": {"term": {"filename.keyword": pdf.name}}, "size": 1},
            )
            hits = result.get("hits", {}).get("hits", [])
            if hits:
                doc_ids.append(hits[0]["_id"])
            else:
                typer.echo(f"  ⚠️  {pdf.name} não encontrado no índice — ignorado")

    if not doc_ids:
        typer.echo("⚠️  Nenhum documento para enriquecer.")
        await es_client.close()
        return

    typer.echo(f"📌 {len(doc_ids)} doc(s) | Operações: {', '.join(sorted(ops))} | Skip-existing: {skip_existing}")
    typer.echo("")

    semaphore = asyncio.Semaphore(concurrency)
    success_count = 0
    error_count = 0
    total = len(doc_ids)

    async def _process(idx: int, doc_id: str) -> None:
        nonlocal success_count, error_count
        async with semaphore:
            # skip_existing: verifica se resumo já existe (proxy de "enriquecido")
            if skip_existing and not force:
                try:
                    doc = await es_client.get(index=index, id=doc_id)
                    if doc.get("_source", {}).get(root, {}).get("resumo_at"):
                        typer.echo(f"  ⏭  [{idx}/{total}] {doc_id} — já enriquecido, pulando")
                        return
                except Exception:
                    pass

            try:
                if {"summary", "entities", "keywords"} <= ops:
                    await svc.enrich_combined(index, doc_id, root)
                else:
                    if "entities" in ops:
                        await svc.enrich_entities(index, doc_id, root)
                    if "keywords" in ops:
                        await svc.enrich_keywords(index, doc_id, root)
                    if "summary" in ops:
                        await svc.enrich_summary(index, doc_id, root)
                if "vectorization" in ops:
                    await svc.enrich_vector(index, doc_id, root)
                if "chunking" in ops:
                    n = await svc.enrich_chunks(index, chunks_index, doc_id, root)
                    if n == 0:
                        typer.echo(f"  ⏭  [{idx}/{total}] {doc_id} — chunking: content < 10000 chars")
                        success_count += 1
                        return
                success_count += 1
                typer.echo(f"  ✅ [{idx}/{total}] {doc_id}")
            except Exception as exc:
                error_count += 1
                typer.echo(f"  ❌ [{idx}/{total}] {doc_id} — {exc}")

    tasks = [_process(i + 1, doc_id) for i, doc_id in enumerate(doc_ids)]
    await asyncio.gather(*tasks)

    await es_client.close()
    typer.echo("")
    typer.echo(f"🏁 Enriquecimento finalizado: {success_count} sucesso, {error_count} erro(s)")


async def _run_enrich_from_es(
    source_type: str,
    ops: set[str],
    batch_size: int,
    force: bool,
    skip_existing: bool,
    concurrency: int,
) -> None:
    from app.clients.es_client import es_client
    from app.providers.factory import get_embedding_provider, get_llm_provider
    from app.services.enrichment import EnrichmentService

    valid_types = ("documentos_ifal_v2", "artefatos")
    if source_type not in valid_types:
        typer.echo(f"❌ source-type inválido: {source_type}. Use: {', '.join(valid_types)}")
        raise typer.Exit(code=1)

    try:
        await es_client.connect()
    except Exception as exc:
        typer.echo(f"❌ Erro ao conectar ao Elasticsearch: {exc}")
        raise typer.Exit(code=1)

    is_artefatos = source_type == "artefatos"
    index = settings.index_artefatos if is_artefatos else settings.index_documentos_ifal_v2
    chunks_index = settings.index_artefatos_chunks if is_artefatos else settings.index_documentos_ifal_v2_chunks
    root = "artefato" if is_artefatos else "ato"

    svc = EnrichmentService(es_client, get_llm_provider(), get_embedding_provider())

    from app.core.exceptions import ValidationError as ServiceValidationError

    # wildcard exige ao menos um char no content (exists não pega string vazia)
    must_clauses: list[dict] = [{"wildcard": {"attachment.content": "*"}}]

    query: dict
    if skip_existing and not force:
        query = {
            "bool": {
                "must": must_clauses,
                "must_not": [{"exists": {"field": f"{root}.resumo_at"}}],
            }
        }
    else:
        query = {"bool": {"must": must_clauses}}

    # contar total antes de iniciar para dar visibilidade
    count_resp = await es_client.search(index=index, body={"query": query, "size": 0})
    total_docs = count_resp.get("hits", {}).get("total", {}).get("value", 0)

    typer.echo(f"📌 Modo: --from-es | Índice: {index} | Total: {total_docs} docs | Batch: {batch_size}")
    typer.echo(f"📌 Operações: {', '.join(sorted(ops))} | Skip-existing: {skip_existing} | Concorrência: {concurrency}")
    typer.echo("")

    if total_docs == 0:
        typer.echo("⚠️  Nenhum documento para processar.")
        await es_client.close()
        return

    semaphore = asyncio.Semaphore(concurrency)
    total_success = 0
    total_errors = 0
    batch_num = 0

    total_skipped = 0

    _GEN_OPS = {"summary", "entities", "keywords"}

    async def _process(doc_id: str) -> bool | None:
        async with semaphore:
            try:
                if _GEN_OPS <= ops:
                    # todas as 3 ops de geração juntas → 1 chamada LLM + 1 update ES
                    await svc.enrich_combined(index, doc_id, root)
                else:
                    if "entities" in ops:
                        await svc.enrich_entities(index, doc_id, root)
                    if "keywords" in ops:
                        await svc.enrich_keywords(index, doc_id, root)
                    if "summary" in ops:
                        await svc.enrich_summary(index, doc_id, root)
                if "vectorization" in ops:
                    await svc.enrich_vector(index, doc_id, root)
                if "chunking" in ops:
                    await svc.enrich_chunks(index, chunks_index, doc_id, root)
                typer.echo(f"  ✅ {doc_id}")
                return True
            except ServiceValidationError as exc:
                typer.echo(f"  ⏭  {doc_id} — {exc}")
                return None
            except Exception as exc:
                typer.echo(f"  ❌ {doc_id} — {exc}")
                return False

    # Scroll: snapshot consistente sem depender de fielddata ou PIT
    first_resp = await es_client.client.search(
        index=index,
        body={"query": query, "_source": False, "size": batch_size},
        scroll="10m",
    )
    scroll_id: str = first_resp.body["_scroll_id"]
    hits = first_resp.body.get("hits", {}).get("hits", [])

    try:
        while hits:
            batch_num += 1
            doc_ids = [h["_id"] for h in hits]

            typer.echo(f"── Lote {batch_num} ({len(doc_ids)} docs) ─────────────────────────────")
            results = await asyncio.gather(*[_process(doc_id) for doc_id in doc_ids])

            batch_ok = sum(1 for r in results if r is True)
            batch_skip = sum(1 for r in results if r is None)
            batch_err = sum(1 for r in results if r is False)
            total_success += batch_ok
            total_skipped += batch_skip
            total_errors += batch_err

            typer.echo(
                f"   ↳ lote {batch_num}: {batch_ok} ✅ / {batch_skip} ⏭  / {batch_err} ❌ "
                f"| acumulado: {total_success} OK / {total_skipped} skip / {total_errors} erro"
            )
            typer.echo("")

            # circuit breaker: lote inteiro falhou → API indisponível, aborta
            real_processed = batch_ok + batch_err
            if real_processed > 0 and batch_err == real_processed:
                typer.echo("🛑 Circuit breaker: lote inteiro com erro — API provavelmente indisponível. Abortando.")
                break

            if len(hits) < batch_size:
                break

            next_resp = await es_client.client.scroll(scroll_id=scroll_id, scroll="10m")
            scroll_id = next_resp.body["_scroll_id"]
            hits = next_resp.body.get("hits", {}).get("hits", [])
    finally:
        try:
            await es_client.client.clear_scroll(scroll_id=scroll_id)
        except Exception:
            pass

    await es_client.close()
    typer.echo(f"🏁 --from-es finalizado: {total_success} ✅ / {total_skipped} ⏭  / {total_errors} ❌  em {batch_num} lote(s)")


@app.command()
def delete() -> None:
    """Apaga documentos ou índices."""
    typer.echo("Not implemented yet")


@app.command()
def stats(
    source_type: str = typer.Option(None, "--source-type", help="documentos_ifal_v2 | artefatos | (omitir = ambos)"),
) -> None:
    """Exibe progresso de enriquecimento por índice."""
    asyncio.run(_run_stats(source_type))


async def _run_stats(source_type: str | None) -> None:
    from app.clients.es_client import es_client

    try:
        await es_client.connect()
    except Exception as exc:
        typer.echo(f"❌ Erro ao conectar ao Elasticsearch: {exc}")
        raise typer.Exit(code=1)

    targets = []
    if source_type == "artefatos" or source_type is None:
        targets.append((settings.index_artefatos, "artefato"))
    if source_type == "documentos_ifal_v2" or source_type is None:
        targets.append((settings.index_documentos_ifal_v2, "ato"))

    for index, root in targets:
        resp = await es_client.search(index=index, body={
            "size": 0,
            "aggs": {
                "total":      {"filter": {"match_all": {}}},
                "com_content":{"filter": {"wildcard": {"attachment.content": "*"}}},
                "entidades":  {"filter": {"exists": {"field": f"{root}.entidades_at"}}},
                "keywords":   {"filter": {"exists": {"field": f"{root}.keywords_at"}}},
                "resumo":     {"filter": {"exists": {"field": f"{root}.resumo_at"}}},
                "embedding":  {"filter": {"exists": {"field": f"{root}.embedding_vector_at"}}},
                "emb_resumo": {"filter": {"match": {f"{root}.embedding_source": "resumo"}}},
                "emb_inicio": {"filter": {"match": {f"{root}.embedding_source": "inicio_documento"}}},
                "chunks":     {"filter": {"exists": {"field": f"{root}.chunking_at"}}},
            },
        })

        aggs = resp.get("aggregations", {})

        def n(key: str) -> int:
            return aggs.get(key, {}).get("doc_count", 0)

        def pct(val: int, total: int) -> str:
            return f"{val / total * 100:.1f}%" if total else "—"

        def bar(val: int, total: int, width: int = 20) -> str:
            filled = round(val / total * width) if total else 0
            return "█" * filled + "░" * (width - filled)

        total = n("total")
        content = n("com_content")
        emb = n("embedding")

        typer.echo(f"\n📊 {index}  —  {total} docs totais  ({content} com conteúdo)")
        typer.echo("─" * 55)

        rows = [
            ("entidades",  n("entidades")),
            ("keywords",   n("keywords")),
            ("resumo",     n("resumo")),
            ("embedding",  emb),
            ("  └ resumo", n("emb_resumo")),
            ("  └ início", n("emb_inicio")),
            ("chunks",     n("chunks")),
        ]

        for label, val in rows:
            base = emb if "└" in label else content
            typer.echo(f"  {label:<14} {bar(val, base)}  {val:>5} / {base:<5}  {pct(val, base):>6}")

        typer.echo("")

    await es_client.close()


# ---------------------------------------------------------------------------
# Entrypoint: python -m app.cli.main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app()
