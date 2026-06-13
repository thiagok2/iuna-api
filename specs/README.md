# Specs — Organização SDD

Esta pasta contém os artefatos Spec-Driven Development (SDD) organizados para o projeto.

Estrutura recomendada:

- `specs/starter/init/` — artefatos iniciais (starter/bootstrap) gerados durante a fase de design do projeto. Contém versões iniciais de Requirements, Design, Tasks e prompts adaptados.
- `specs/features/` — features aprovadas e prontas para serem transformadas em tasks/implementações.
- `specs/bugfixes/` — documentos Bugfix Requirements e designs relacionados a correções.
- `specs/enhancements/` — propostas de melhorias e refatorações planejadas.

Uso:
- Valide e aprova o documento em `specs/starter/init` antes de movê-lo para `specs/features/`.
- Mantenha rastreabilidade: cada task deve referenciar o requisito que implementa.
- Atualize `specs/README.md` conforme a convenção evolui.

Observação: os documentos canônicos da metodologia (`metodologia-spec-driven-development.md` e `sdd-prompt-llm.md`) ficam na **raiz do projeto** como fonte única de verdade. Não os duplique em subpastas de `specs/`.
