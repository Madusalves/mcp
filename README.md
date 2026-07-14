# Design de Solução: Doc-Agent (MCP de Documentação Automatizada)

> Documento de arquitetura para uma solução que **gera documentação automaticamente** a
> partir do que já existe (código, endpoints, histórico), deixando para a pessoa apenas
> revisar e aprovar. Objetivo: eliminar o custo de tempo que hoje impede a documentação
> de acontecer.

- **Autor:** madu
- **Data:** 2026-07-13
- **Status:** Proposta para discussão
- **Stack alvo:** .NET / C# · Microsoft Agent Framework (MAF) · Azure OpenAI · Azure DevOps · Microsoft Loop

---

## 1. Problema

A documentação não existe não por falta de padrão, mas por falta de tempo: escrever à mão
compete com entregar features, e perde sempre. O conhecimento fica na cabeça das pessoas e
vira risco (fator ônibus).

**Objetivo:** reduzir o esforço humano de documentar de "escrever do zero" para "revisar um
rascunho pronto". Se o rascunho já vem 80% pronto a partir do código, o custo cai a ponto
de a documentação finalmente acontecer.

## 2. Princípio central: o agente rascunha, o humano aprova

Não automatizamos a *decisão*, automatizamos o *trabalho braçal*. O agente:

1. Lê o que já é fonte da verdade (código, endpoints, commits, PRs).
2. Gera o rascunho no padrão da empresa (os templates de README, ADR, arquitetura, runbook).
3. Abre para revisão humana — nada é publicado sem aprovação (human-in-the-loop).

Isso é seguro (ninguém publica doc errada sozinho) e é exatamente o padrão que o MAF
suporta nativamente com *tool approval workflows*.

## 3. Por que MCP + MAF (e não só uma skill)

Uma skill guia a *escrita*, mas não *lê o repositório* nem *escreve no Loop*. Este caso
exige ação sobre sistemas reais — por isso um servidor MCP. E o MAF é a escolha coerente
porque é Microsoft-nativo: fala com Azure OpenAI, Azure DevOps e Loop sem sair do ecossistema
Azure, o que resolve governança e segurança de dados de antemão.

Regra: **skill para padronizar a escrita; MCP/MAF para automatizar a coleta e a publicação.**
Os dois convivem — a skill pode até ser o "guia de estilo" que o agente carrega.

## 4. Arquitetura (visão de contexto)

```mermaid
flowchart TD
    Dev[Desenvolvedor / Você] -->|"documenta o sistema X"| Client[Cliente MCP\nVS Code / IDE / Claude]
    Client -->|MCP over HTTP| Agent[Doc-Agent\nMAF em C#]
    Agent -->|raciocínio / geração| AOAI[Azure OpenAI]
    Agent -->|lê código, PRs, commits| ADO[Azure DevOps\nRepos + API]
    Agent -->|publica regra de negócio| Loop[Microsoft Loop\nvia Microsoft Graph]
    Agent -->|abre PR com a doc| ADO
    Dev -->|revisa e aprova o PR| ADO
```

Tudo dentro do tenant Azure da empresa. Nenhum dado de código trafega para fora.

## 5. As ferramentas que o MCP exporia

Cada ferramenta é um verbo objetivo. Comece com poucas e sólidas.

| Ferramenta MCP | O que faz | Fonte | Saída |
|---|---|---|---|
| `auditar_docs` | Varre um repo e lista o que está sem README/ADR/runbook | Azure DevOps | Relatório de lacunas |
| `gerar_readme` | Monta o README a partir da estrutura do projeto e do `.csproj` | Código .NET | Rascunho em PR |
| `analisar_arquitetura` | Infere o estilo arquitetural (Clean Architecture, MVC, Hexagonal) pelo grafo de `ProjectReference` entre `.csproj` e aponta violações de dependência entre camadas | Código .NET | Relatório de arquitetura |
| `gerar_api_docs` | Extrai endpoints de controllers/minimal APIs + comentários XML | Código .NET | Doc de API em PR |
| `rascunhar_adr` | Sugere ADRs a partir do histórico de commits/PRs relevantes | Git history | Rascunho de ADR |
| `gerar_diagrama` | Gera diagrama C4 (Mermaid) a partir de dependências do projeto | Código .NET | `.md` com Mermaid |
| `publicar_regra_no_loop` | Traduz uma regra técnica para linguagem de GP e publica | Spec + Graph API | Página no Loop |

> Detalhe .NET que facilita muito: se o time habilitar **geração de XML docs** e
> **comentários `///`**, o agente extrai a documentação de API quase pronta.

## 6. Fluxo de ponta a ponta (exemplo real)

1. Você roda `auditar_docs` no repositório do sistema crítico do piloto.
2. O agente devolve: "faltam README, 2 ADRs e o runbook de deploy".
3. Você roda `gerar_readme` e `gerar_diagrama` — o agente lê o código, chama o Azure OpenAI
   e **abre um Pull Request** no Azure DevOps com os rascunhos.
4. Você revisa o PR como revisaria código, ajusta o que for preciso, aprova e faz merge.
5. Para as regras de negócio, `publicar_regra_no_loop` cria a página no Loop em linguagem de GP.

O humano nunca sai do controle; só deixa de escrever da folha em branco.

## 7. Stack técnico

- **Servidor MCP:** projeto .NET (C#) usando o SDK MCP + Microsoft Agent Framework. O agente
  é convertido em ferramenta MCP e servido por HTTP (`.AsAIFunction()` → MCP tool).
- **Motor de IA:** Azure OpenAI (modelo de chat implantado no recurso da empresa).
- **Acesso ao código:** Azure DevOps REST API / client library (ler repos, abrir PRs).
- **Publicação no Loop:** Microsoft Graph API (Loop é construído sobre o Graph/Fluid).
- **Autenticação:** Entra ID (Azure AD) com managed identity — sem segredos no código.
- **Hospedagem:** Azure App Service ou Container Apps, dentro da rede corporativa.

## 8. Rollout em fases (não construa tudo de uma vez)

**Fase 0 — Prova de conceito (1 ferramenta):** só `gerar_readme`, rodando local, contra um
repo. Objetivo: provar que o rascunho gerado é bom o bastante. Baixo custo, alta prova de valor.

**Fase 1 — Leitura + geração:** adicione `auditar_docs`, `gerar_api_docs`, `gerar_diagrama`.
Ainda sem publicar nada — só abre PR. Aqui já entrega valor real ao time.

**Fase 2 — Publicação e Loop:** `rascunhar_adr` e `publicar_regra_no_loop` via Graph. Aqui
fecha o ciclo técnico ↔ negócio.

**Fase 3 — Automação contínua:** um pipeline no Azure DevOps roda `auditar_docs`
semanalmente e abre PRs de doc automaticamente quando detecta lacuna.

## 9. Riscos e trade-offs (pensamento de arquiteto)

- **Qualidade do rascunho:** IA pode inventar. Mitigação: sempre via PR com revisão humana;
  nunca publicação direta. O agente sugere, não decide.
- **Custo de tokens:** varreduras grandes custam. Mitigação: escopo por repo, cache, rodar
  sob demanda antes de rodar contínuo.
- **Manutenção do próprio agente:** é software de produção, precisa de dono. Mitigação:
  começar mínimo (1 ferramenta) e só crescer com uso comprovado.
- **Segurança de código-fonte:** por isso tudo em Azure OpenAI no tenant da empresa —
  o código não sai do perímetro.
- **Não vira desculpa para não pensar:** o agente documenta o "o quê" e o "como"; o "por quê"
  (decisões) ainda precisa de julgamento humano. Ele acelera, não substitui o arquiteto.

## 10. Como isso te posiciona

Escrever documentação te faz útil. **Construir a plataforma que faz a empresa inteira
documentar sozinha** te faz estratégico. Este projeto te move de "quem documenta" para "quem
projetou o sistema de documentação" — que é papel de arquiteto de soluções, exatamente o que
o teu curso trata. É um artefato concreto para levar à liderança como proposta de iniciativa.

## 11. Próximos passos sugeridos

1. Validar com o time se XML docs / comentários `///` estão (ou podem ser) habilitados nos projetos.
2. Confirmar acesso a um recurso de Azure OpenAI e permissões no Azure DevOps.
3. Construir a Fase 0 (`gerar_readme`) contra o repo do piloto e medir a qualidade do rascunho.
4. Com o resultado em mãos, apresentar este design como proposta de iniciativa.