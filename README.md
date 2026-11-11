# 💰 Controle Financeiro em Python

Aplicação de linha de comando para controle de finanças pessoais: registre receitas e despesas, acompanhe seu saldo, gere relatórios mensais e exporte seus dados para CSV.

Feito apenas com a **biblioteca padrão do Python** — nenhuma dependência externa.

## Funcionalidades

| # | Função | Descrição |
|---|--------|-----------|
| 1 | Adicionar receita | Registra uma entrada com descrição, valor, categoria e data |
| 2 | Adicionar despesa | Registra uma saída com descrição, valor, categoria e data |
| 3 | Listar transações | Mostra todas as transações ordenadas por data |
| 4 | Buscar por ID | Mostra uma transação específica pelo ID |
| 5 | Editar transação | Altera descrição, valor, categoria e/ou data pelo ID (Enter mantém o valor atual) |
| 6 | Excluir transação | Remove uma transação pelo ID, após confirmação |
| 7 | Mostrar saldo | Total de receitas, despesas e saldo atual |
| 8 | Filtrar por categoria | Lista as transações de uma categoria e o total dela |
| 9 | Relatório mensal | Resumo do mês com gastos por categoria (com percentual e gráfico em barras) |
| 10 | Exportar dados | Gera um arquivo `.csv` pronto para abrir no Excel |
| 0 | Sair | Encerra o programa |

Os dados são salvos automaticamente em `dados/transacoes.json` — inclusive edições e exclusões, que continuam valendo depois de reiniciar o programa.

## Validação e tratamento de erros

### Entrada de dados

| Campo | Regra |
|-------|-------|
| ID | Número inteiro positivo. ID inexistente gera `TransacaoNaoEncontrada` |
| Descrição | Texto não vazio |
| Valor | Número **finito** de no mínimo R$ 0,01 (`inf`, `-inf` e `nan` são recusados). Arredondado para 2 casas |
| Categoria | Texto; se ficar vazio, vira `outros` |
| Data | Precisa ser uma data válida (`datetime` é convertido para `date`) |

- No menu, se o ID não existir ou for inválido, o programa pede de novo. **Enter vazio cancela** a operação.
- Na edição, todos os campos são validados **antes** de alterar qualquer coisa, então a transação nunca fica pela metade.
- Se a edição não mudar nada, o arquivo não é regravado e aparece "Nenhuma alteração feita".

### Carregamento do arquivo JSON

Ao abrir, o programa confere o arquivo `dados/transacoes.json`. Se encontrar algum problema, mostra o motivo e **encerra sem apagar nem sobrescrever os dados**:

- JSON corrompido (informa a linha e a coluna do erro)
- Arquivo que não está em UTF-8 ou que não pode ser aberto
- Conteúdo que não é uma lista de transações
- Registro com campo faltando ou inválido (informa qual registro, ex.: `registro 3 inválido: valor inválido: 'abc'`)
- IDs repetidos

### Gravação do arquivo

- Os valores são salvos como texto (`"valor": "16.00"`) para não perder precisão. Arquivos antigos, com o valor como número (`16.0`), continuam sendo lidos normalmente.
- O arquivo é gravado primeiro em um `.tmp` e só depois substitui o original, então uma falha no meio da escrita não corrompe o JSON.
- Se não for possível salvar (disco cheio, sem permissão etc.), a alteração é **desfeita na memória** e o usuário é avisado — o programa continua funcionando.

### Exceções do projeto

| Exceção | Quando acontece |
|---------|-----------------|
| `TransacaoNaoEncontrada` | Não existe transação com o ID informado (subclasse de `ValueError`) |
| `ArquivoDeDadosInvalido` | O JSON está corrompido ou tem registros inválidos |
| `ErroAoSalvar` | Não foi possível gravar as transações no arquivo |

## Precisão dos valores (`Decimal`)

Os valores em dinheiro usam `Decimal` em vez de `float`. Com `float`, contas simples dão resultados errados:

```python
>>> 0.1 + 0.2
0.30000000000000004
>>> round(2.675, 2)
2.67
```

Com `Decimal`, as somas são exatas e o arredondamento segue o padrão escolar (`ROUND_HALF_UP`): `2,675` vira `2,68`. A conversão fica centralizada na função `para_decimal()` do `modelo.py`.

## Como executar

Requisito: Python 3.10 ou superior.

```bash
cd controle_financeiro
python main.py
```

Rodar os testes:

```bash
python -m unittest -v
```

## Estrutura do projeto

```
controle_financeiro/
├── main.py              # Interface (menu, entrada e exibição de dados)
├── gerenciador.py       # Regras de negócio, validação, persistência JSON e exportação CSV
├── modelo.py            # Dataclass Transacao, conversão para Decimal e validação dos dados lidos do JSON
├── test_gerenciador.py  # Testes automatizados (unittest)
├── dados/               # Criada automaticamente — banco de dados JSON
└── exportacoes/         # Criada automaticamente — arquivos CSV exportados
```

A interface (`main.py`) fica separada da lógica (`gerenciador.py`), o que permite testar as regras de negócio sem depender do `input()` e facilita trocar a interface no futuro (por exemplo, por uma interface gráfica ou web).

## Histórico de alterações

### Valores com `Decimal`

- `float` substituído por `Decimal` em todo o projeto (modelo, gerenciador, totais, relatório e interface)
- Nova função `para_decimal()` no `modelo.py`, que converte e arredonda para 2 casas com `ROUND_HALF_UP`
- Valores salvos no JSON como texto; arquivos antigos com valor numérico continuam compatíveis
- Valores que arredondam para zero (ex.: `0,004`) passam a ser recusados
- Removidos os `round()` espalhados pelo código, já que as somas com `Decimal` são exatas
- Novos testes de precisão: `0,1 + 0,2`, várias somas pequenas, arredondamento de meio centavo e compatibilidade com o formato antigo

### Busca, edição/exclusão e erros ao salvar

- Nova opção **4 - Buscar transação por ID** no menu (as opções seguintes passaram a ser 5 a 10)
- Busca, edição e exclusão pedem o ID de novo quando ele não existe; Enter cancela
- Validação de ID e dos tipos de cada campo em `adicionar` e `editar`
- Edição sem mudanças não regrava o arquivo
- Gravação segura com arquivo temporário
- Nova exceção `ErroAoSalvar`: se a gravação falhar, adicionar, editar e excluir desfazem a alteração
- Novos testes: busca por ID, IDs inválidos, edição com dados errados e simulação de falha no disco

### Validação dos dados e do arquivo JSON

- `_validar_valor` passou a recusar valores não finitos (`inf`, `nan`), também na digitação do menu
- `_carregar()` trata JSON corrompido com a nova exceção `ArquivoDeDadosInvalido`, sem apagar os dados
- `Transacao.de_dict()` valida tipo, valor, data e os demais campos antes de aceitar um registro
- Registros com IDs repetidos são recusados no carregamento
- Novos testes para valores não finitos e para arquivos JSON inválidos

### Primeira versão

- Cadastro de receitas e despesas, listagem, edição e exclusão
- Saldo, filtro por categoria, relatório mensal e exportação para CSV

## Conceitos praticados

- Programação orientada a objetos e `dataclasses`
- Type hints
- Leitura e escrita de arquivos (`json`, `csv`, `pathlib`)
- Manipulação de datas com `datetime`
- Valores monetários precisos com `decimal`
- Validação de entrada e tratamento de exceções (incluindo exceções próprias)
- Gravação segura de arquivos e desfazer alterações em caso de erro
- Testes automatizados com `unittest` e `unittest.mock`

## Próximos passos (ideias)

- [x] Editar e excluir transações
- [x] Buscar transação por ID
- [x] Validar os dados carregados do JSON
- [x] Usar `Decimal` no lugar de `float` para maior precisão monetária
- [ ] Banco de dados SQLite
- [ ] Gráficos com `matplotlib`
- [ ] Interface gráfica (Tkinter) ou web (Flask/Streamlit)
