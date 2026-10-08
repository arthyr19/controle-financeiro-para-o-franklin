# 💰 Controle Financeiro em Python

Aplicação de linha de comando para controle de finanças pessoais: registre receitas e despesas, acompanhe seu saldo, gere relatórios mensais e exporte seus dados para CSV.

Feito apenas com a **biblioteca padrão do Python** — nenhuma dependência externa.

## Funcionalidades

| # | Função | Descrição |
|---|--------|-----------|
| 1 | Adicionar receita | Registra uma entrada com descrição, valor, categoria e data |
| 2 | Adicionar despesa | Registra uma saída com descrição, valor, categoria e data |
| 3 | Listar transações | Mostra todas as transações ordenadas por data |
| 4 | Mostrar saldo | Total de receitas, despesas e saldo atual |
| 5 | Filtrar por categoria | Lista as transações de uma categoria e o total dela |
| 6 | Relatório mensal | Resumo do mês com gastos por categoria (com percentual e gráfico em barras) |
| 7 | Exportar dados | Gera um arquivo `.csv` pronto para abrir no Excel |
| 8 | Sair | Encerra o programa |

Os dados são salvos automaticamente em `dados/transacoes.json`.

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
├── gerenciador.py       # Regras de negócio, persistência JSON e exportação CSV
├── modelo.py            # Dataclass Transacao
├── test_gerenciador.py  # Testes automatizados (unittest)
├── dados/               # Criada automaticamente — banco de dados JSON
└── exportacoes/         # Criada automaticamente — arquivos CSV exportados
```

A interface (`main.py`) fica separada da lógica (`gerenciador.py`), o que permite testar as regras de negócio sem depender do `input()` e facilita trocar a interface no futuro (por exemplo, por uma interface gráfica ou web).

## Conceitos praticados

- Programação orientada a objetos e `dataclasses`
- Type hints
- Leitura e escrita de arquivos (`json`, `csv`, `pathlib`)
- Manipulação de datas com `datetime`
- Validação de entrada e tratamento de exceções
- Testes automatizados com `unittest`

## Próximos passos (ideias)

- [ ] Editar e excluir transações
- [ ] Usar `Decimal` no lugar de `float` para maior precisão monetária
- [ ] Banco de dados SQLite
- [ ] Gráficos com `matplotlib`
- [ ] Interface gráfica (Tkinter) ou web (Flask/Streamlit)
